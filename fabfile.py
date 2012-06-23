from __future__ import with_statement
from fabric.api import run, sudo, put, env, require, local, settings, prefix, cd
from fabric.contrib.console import confirm
import os


env.sites_dir           = "/srv/sites"
env.virtualenv_dir      = "/virtualenvs"
env.git_repo            = "git://github.com/munchie/django-example-project.git"
env.virtualenv          = "webapp"
env.project_name        = "myproject"
env.code_dir            = os.path.join(env.sites_dir, env.virtualenv)
env.project_dir         = os.path.join(env.code_dir, env.project_name)
env.db_name             = "webapp"
env.db_user             = "webapp"
env.bash_profile        = ".bash_profile"


# These are the packages we need to install using aptitude install
INSTALL_PACKAGES_WEB = [
    "vim",
    "ntp",
    "git",
    "python2.7-dev",
    "python-setuptools",
    "build-essential",
    "subversion",
    "mercurial",
    "nginx",
    "libevent-dev",
    "postgresql-server-dev-9.1",
    "postgresql-client",
    "libpq-dev"
]


INSTALL_PACKAGES_DB = [
    "vim",
    "ntp",
    "git",
    "python2.7-dev",
    "python-setuptools",
    "build-essential",
    "postgresql",
    "postgresql-client"
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


def vagrant_web():
    """Setup local vagrant web server settings"""
    env.hosts           = ["vagrant-web1", "vagrant-web2"]
    env.user            = "vagrant"
    env.key_filename    = "~/.vagrant.d/insecure_private_key"
    env.django_settings = "settings.development"
    env.branch          = "master"
    env.bash_profile    = ".vagrant_profile"
    env.package_list    = INSTALL_PACKAGES_WEB


def vagrant_db():
    """Setup local vagrant db server settings"""
    env.hosts        = ["vagrant-db1"]
    env.user         = "vagrant"
    env.key_filename = "~/.vagrant.d/insecure_private_key"
    env.package_list = INSTALL_PACKAGES_DB


# Provision instance
def setup_vagrant_web():
    """Bootstraps the vagrant web environment"""
    require('hosts', provided_by=[vagrant_web])
    stop_web_processes()
    install_packages()
    make_virtualenv()
    setup_sites_dir()
    clone_repo()
    pull()
    requirements()
    syncdb()
    migrate()
    collectstatic()
    setup_nginx()
    setup_gunicorn()
    gunicorn_config()
    nginx_config()
    start_web_processes()


def setup_vagrant_db():
    """Bootstraps the vagrant db environment"""
    require('hosts', provided_by=[vagrant_db])
    stop_db_process()
    install_packages()
    setup_sites_dir()
    clone_repo()
    setup_db()
    db_config()
    start_db_process()
    create_db_and_user()


# Sub commands
def start_web_processes():
    """Starts nginx and gunicorn"""
    sudo("service nginx start")
    sudo("start gunicorn")


def stop_web_processes():
    """Stops nginx and gunicorn"""
    with settings(warn_only=True):
        sudo("service nginx stop")
        sudo("stop gunicorn")


def start_db_process():
    """Starts postgresql"""
    sudo("service postgresql start")


def stop_db_process():
    """Stops postgresql"""
    with settings(warn_only=True):
        sudo("service postgresql stop")


def install_packages():
    """Install required packages"""
    sudo("aptitude update")
    sudo("aptitude -y install %s" % " ".join(env.package_list))
    sudo("easy_install pip")
    sudo("pip install virtualenv virtualenvwrapper")


def make_virtualenv():
    """Create the virtualenv and set the DJANGO_SETTINGS_MODULE"""
    # create dir for storing virtualenvs
    sudo("mkdir -p %(virtualenv_dir)s" % env)
    sudo("chown %(user)s:%(user)s %(virtualenv_dir)s" % env)

    # setup virtualenvwrapper in the user's .bash_profile. Note see this post about why we use .bash_profile instead of .bashrc
    # http://brianna.laugher.id.au/blog/62/getting-virtualenvwrapper-and-fabric-to-play-nice
    put('config/%(bash_profile)s' % env, '~/.bash_profile')
    with settings(warn_only=True):
        if run('grep "source /usr/local/bin/virtualenvwrapper.sh" ~/.bashrc').failed:
            run('cat ~/.bash_profile >> ~/.bashrc')

    # in case the virtualenv already exists we remove it
    with settings(warn_only=True):
        run("rmvirtualenv %(virtualenv)s" % env)

    # create the virtualenv and add project_dir to PYTHONPATH
    run("mkvirtualenv --no-site-packages %(virtualenv)s" % env)
    with prefix('workon %(virtualenv)s' % env):
        run("add2virtualenv %(project_dir)s" % env)

    # setup DJANGO_SETTINGS_MODULE in virtualenvwrapper's postactivate and postdeactivate hooks
    run('echo "export DJANGO_SETTINGS_MODULE=%(django_settings)s" >> %(virtualenv_dir)s/%(virtualenv)s/bin/postactivate' % env)
    run('echo "unset DJANGO_SETTINGS_MODULE" >> %(virtualenv_dir)s/%(virtualenv)s/bin/postdeactivate' % env)


def setup_sites_dir():
    """Make the sites directory for deploying the source code"""
    # setup sites location
    sudo("mkdir -p %(sites_dir)s" % env)
    sudo("chown %(user)s:%(user)s %(sites_dir)s" % env)


def setup_db():
    """Create the postgres db and db user for the app"""
    with cd("/etc/postgresql/9.1/main"):
        # remove the default config files
        sudo("rm -f postgresql.conf pg_hba.conf")


def db_config():
    """Updates the postgresql config files"""
    with cd("/etc/postgresql/9.1/main"):
        sudo("rm -f postgresql.conf pg_hba.conf")
        sudo("ln -sf %(code_dir)s/config/postgresql/postgresql.conf ." % env)
        sudo("ln -sf %(code_dir)s/config/postgresql/pg_hba.conf ." % env)


def create_db_and_user():
    """Creates the db and user"""
    # warn if db user or db already exists
    with settings(warn_only=True):
        # create db user (not a superuser, can create db, can't create roles, no password)
        sudo("createuser %(db_user)s -S -d -R" % env, user="postgres")
        # create db owned by db user
        sudo("createdb %(db_name)s -O %(db_user)s" % env, user="postgres")


def setup_gunicorn():
    """Setup after initial install of gunicorn"""
    # create gunicorn log directory
    sudo("mkdir -p /var/log/gunicorn")


def gunicorn_config():
    """Updates the gunicorn upstart config file"""
    with cd("/etc/init"):
        sudo("rm -f gunicorn.conf")
        sudo("cp %(code_dir)s/config/gunicorn/gunicorn.conf ." % env)


def setup_nginx():
    """Setup after initial install of nginx"""
    with cd("/etc/nginx"):
        # remove all the basic installed stuff
        sudo("rm -rf conf.d/ fastcgi_params koi-* nginx.conf sites-* win-utf")


def nginx_config():
    """Updates the nginx config file"""
    with cd("/etc/nginx"):
        sudo("rm -f nginx.conf")
        sudo("ln -sf %(code_dir)s/config/nginx/nginx.conf ." % env)


def clone_repo():
    """Clone the git repo to the code directory"""
    with settings(warn_only=True):
        if run('test -d %(code_dir)s' % env).failed:
            run('git clone %(git_repo)s %(code_dir)s' % env)


def push():
    """Push new code to origin master"""
    local('git push origin master')


def pull():
    """Pull new code"""
    with cd(env.code_dir):
        run('git pull')


def requirements():
    """Updates the requirements in the virtualenv"""
    with cd(env.code_dir):
        with prefix('workon %(virtualenv)s' % env):
            run("pip install -r requirements.txt")


def syncdb():
    """Syncs the database"""
    with prefix('workon %(virtualenv)s' % env):
        run('django-admin.py syncdb')


def migrate(app=None):
    """Migrate the database"""
    with prefix('workon %(virtualenv)s' % env):
        if app:
            run('django-admin.py migrate %s' % app)
        else:
            run('django-admin.py migrate')


def collectstatic():
    """Collect static files into static folder"""
    with settings(warn_only=True):
        with prefix('workon %(virtualenv)s' % env):
            run('django-admin.py collectstatic -l')


def restart_gunicorn():
    """Restarts gunicorn"""
    with settings(warn_only=True):
        # Note: Upstart reload or restart does not pick up changes to the conf file.
        sudo("stop gunicorn")
        sudo("start gunicorn")


def reload_nginx():
    """Reloads nginx"""
    with settings(warn_only=True):
        sudo("service nginx reload")


def deploy():
    """Deploy code to directory that serves the app"""
    pull()
    requirements()
    migrate()
    collectstatic()
    restart_gunicorn()
    reload_nginx()


def test():
    """Run unit tests"""
    with settings(warn_only=True):
        result = local('./manage.py test', capture=True)
    if result.failed and not confirm("Tests failed. Continue anyway?"):
        abort("Aborting at user request.")
