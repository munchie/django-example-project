
# setup virtualenv and virtualenvwrapper
if [ $USER == ubuntu ]; then
  export WORKON_HOME=/virtualenvs
  source /usr/local/bin/virtualenvwrapper.sh
fi

# Show current git branch
function parse_git_branch {
  git branch --no-color 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/(\1)/'
}
PS1="\h:\W\$(parse_git_branch) \u\$ "

