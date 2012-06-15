from __future__ import with_statement
from fabric.api import run, sudo, put, env, require, local, settings
from fabric.contrib.console import confirm
import os
import subprocess


env.sites_dir           = "/srv/sites"
env.virtualenv_dir      = ".virtualenvs"
env.git_repo            = "git://github.com/munchie/django-example-project.git"
env.virtualenv          = "webapp"
env.nginx_conf          = "nginx_webapp.conf"
env.nginx               = "nginx_webapp"
env.gunicorn_conf       = "gunicorn_webapp.conf"
env.gunicorn            = "gunicorn_webapp"
env.project_name        = "myproject"
env.deploy_user         = "deploy"
env.deploy_user_home    = "/home/deploy"
env.code_dir            = os.path.join(env.sites_dir, env.virtualenv)
env.project_dir         = os.path.join(env.code_dir, env.project_name)


# These are the packages we need to install using aptitude install
INSTALL_PACKAGES = [
    "ntp",
    "git",
    "python2.7-dev",
    "python-setuptools",
    "build-essential",
    "subversion",
    "mercurial",
    "nginx",
    "libevent-dev",
    "postgresql",
    "postgresql-server-dev-9.1",
    "libpq-dev"
]


# Environments
def production():
    """Setup production settings"""
    env.hosts           = ["ec2-107-22-109-221.compute-1.amazonaws.com"]
    env.user            = "ubuntu"
    env.key_filename    = "~/.ec2/ubuntu1.pem"
    env.django_settings = "settings.production"
    env.branch          = "stable"


def staging():
    """Setup staging settings"""
    env.hosts           = ["ec2-107-22-109-221.compute-1.amazonaws.com"]
    env.user            = "ubuntu"
    env.key_filename    = "~/.ec2/ubuntu1.pem"
    env.django_settings = "settings.development"
    env.branch          = "master"


def vagrant():
    """Setup local vagrant settings"""
    raw_ssh_config      = subprocess.Popen(["vagrant", "ssh-config"], stdout=subprocess.PIPE).communicate()[0]
    ssh_config          = dict([l.strip().split() for l in raw_ssh_config.split("\n") if l])
    env.hosts           = ["127.0.0.1:%s" % ssh_config["Port"]]
    env.user            = ssh_config["User"]
    env.key_filename    = ssh_config["IdentityFile"]
    env.django_settings = "settings.development"
    env.branch          = "master"


# Provision instance
def setup_vagrant():
    """Bootstraps the Vagrant environment"""
    require('hosts', provided_by=[vagrant])
    stop_processes()
    add_deploy_user()
    install_packages()
    make_virtualenv()
    setup_sites_dir()
    setup_db()
    clone_repo()
    pull()
    requirements()
    migrate()
    collectstatic()
    gunicorn_config()
    nginx_config()
    start_processes()


# Sub commands
def start_processes():
    """Starts nginx and gunicorn"""
    sudo("start %(nginx)s" % env)
    sudo("start %(gunicorn)s" % env)


def stop_processes():
    """Stops nginx and gunicorn"""
    with settings(warn_only=True):
        sudo("stop %(nginx)s" % env)
        sudo("stop %(gunicorn)s" % env)


def add_deploy_user():
    """Add a deploy user for deploying the code"""
    with settings(warn_only=True):
        if run("id %(deploy_user)s" % env).failed:
            sudo("useradd -d %(deploy_user_home)s -m -s /bin/bash deploy" % env)


def install_packages():
    """Install required packages"""
    sudo("aptitude update")
    sudo("aptitude -y install %s" % " ".join(INSTALL_PACKAGES))
    sudo("easy_install pip")
    sudo("pip install virtualenv virtualenvwrapper")
    # remove default nginx configuration
    sudo("rm -f /etc/nginx/sites-enabled/default")
    # create gunicorn log directory
    sudo("mdkir -p /var/log/gunicorn")


def make_virtualenv():
    """Create the virtualenv and set the DJANGO_SETTINGS_MODULE"""
    # setup virtualenvwrapper in the user's .bash_profile. Note see this post about why we use .bash_profile instead of .bashrc
    # http://brianna.laugher.id.au/blog/62/getting-virtualenvwrapper-and-fabric-to-play-nice
    put('config/.bash_profile', '%(deploy_user_home)s/.bash_profile' % env)
    with settings(warn_only=True):
        if sudo('grep "source /usr/local/bin/virtualenvwrapper.sh" ~/.bashrc', user=env.deploy_user).failed:
            sudo('cat ~/.bash_profile >> ~/.bashrc', user=env.deploy_user)

    # in case the virtualenv already exists we remove it
    with settings(warn_only=True):
        sudo("rmvirtualenv %(virtualenv)s" % env, user=env.deploy_user)

    # create the virtualenv and add project_dir to PYTHONPATH
    sudo("mkvirtualenv --no-site-packages %(virtualenv)s" % env, user=env.deploy_user)
    with prefix('workon %(virtualenv)s' % env):
        sudo("add2virtualenv %(project_dir)s" % env, user=env.deploy_user)

    # setup DJANGO_SETTINGS_MODULE in virtualenvwrapper's postactivate and postdeactivate hooks
    sudo('echo "export DJANGO_SETTINGS_MODULE=%(django_settings)s" >> ~/%(virtualenv_dir)s/%(virtualenv)s/bin/postactivate' % env, user=env.deploy_user)
    sudo('echo "unset DJANGO_SETTINGS_MODULE >> ~/%(virtualenv_dir)s/%(virtualenv)s/bin/postdeactivate"' % env, user=env.deploy_user)


def setup_sites_dir():
    """Make the sites directory for deploying the source code"""
    # setup sites location
    sudo("mkdir -p %(sites_dir)s" % env)
    sudo("chown %(deploy_user)s:%(deploy_user)s %(sites_dir)s" % env)


def setup_db():
    """Create the postgres db and db user for the app"""
    # warn if db user or db already exists
    with settings(warn_only=True):
        # create db user (not a superuser, can create db, can't create roles, requires password)
        sudo("createuser %(db_user)s -S -d -R -P" % env, user="postgres")
        # create db owned by db user
        sudo("createdb %(db_name)s -O %(db_user)s" % env, user="postgres")


def clone_repo():
    """Clone the git repo to the code directory"""
    with settings(warn_only=True):
        if run('test -d %(code_dir)s' % env).failed:
            sudo('git clone %(git_repo)s %(code_dir)s' % env, user=env.deploy_user)


def push():
    """Push new code to origin master"""
    local('git push origin master')


def pull():
    """Pull new code"""
    with cd(env.code_dir):
        sudo('git pull', user=env.deploy_user)


def requirements():
    """Updates the requirements in the virtualenv"""
    with cd(env.code_dir):
        with prefix('workon %(virtualenv)s' % env):
            sudo("pip install -r requirements.txt", user=env.deploy_user)


def syncdb():
    """Syncs the database"""
    with prefix('workon %(virtualenv)s' % env):
        sudo('django-admin.py syncdb', user=env.deploy_user)


def migrate(app=None):
    """Migrate the database"""
    with prefix('workon %(virtualenv)s' % env):
        if app:
            sudo('django-admin.py migrate %s' % app, user=env.deploy_user)
        else:
            sudo('django-admin.py migrate', user=env.deploy_user)


def collectstatic():
    """Collect static files into static folder"""
    with settings(warn_only=True):
        with prefix('workon %(virtualenv)s' % env):
            sudo('django-admin.py collectstatic -l', user=env.deploy_user)


def gunicorn_config():
    """Updates the gunicorn upstart config file"""
    sudo("cp -f %(code_dir)s/config/%(gunicorn_conf)s /etc/init/%(gunicorn_conf)s" % env)


def restart_gunicorn():
    """Restarts gunicorn"""
    with settings(warn_only=True):
        # Note: Upstart reload does not pick up changes to the conf file.
        sudo("stop %(gunicorn)s" % env)
        sudo("start %(gunicorn)s" % env)


def nginx_config():
    """Updates the nginx config file"""
    sudo("cp -f %(code_dir)s/config/%(nginx_conf)s /etc/nginx/sites-available/%(nginx_conf)s" % env)
    sudo("ln -sf /etc/nginx/sites-available/%(nginx_conf)s /etc/nginx/sites-enabled" % env)


def reload_nginx():
    """Reloads nginx"""
    with settings(warn_only=True):
        sudo("nginx -s reload")


def deploy():
    """Deploy code to directory that serves the app"""
    pull()
    requirements()
    migrate()
    collectstatic()
    gunicorn_config()
    nginx_config()
    restart_gunicorn()
    reload_nginx()


def test():
    """Run unit tests"""
    with settings(warn_only=True):
        result = local('./manage.py test', capture=True)
    if result.failed and not confirm("Tests failed. Continue anyway?"):
        abort("Aborting at user request.")
