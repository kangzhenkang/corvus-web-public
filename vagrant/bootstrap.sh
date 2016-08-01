#! /usr/bin/env bash

CORVUS_HOME=/home/vagrant
CORVUS_VAGRANT=$CORVUS_HOME/corvus-web/vagrant
BOWER=$CORVUS_HOME/.node/bin/bower
GULP=$CORVUS_HOME/.node/bin/gulp

cat > /etc/apt/sources.list <<EOF
deb http://cn.archive.ubuntu.com/ubuntu/ trusty main restricted universe multiverse
deb http://cn.archive.ubuntu.com/ubuntu/ trusty-security main restricted universe multiverse
deb http://cn.archive.ubuntu.com/ubuntu/ trusty-updates main restricted universe multiverse
deb http://cn.archive.ubuntu.com/ubuntu/ trusty-proposed main restricted universe multiverse
deb http://cn.archive.ubuntu.com/ubuntu/ trusty-backports main restricted universe multiverse
EOF

curl -sL https://deb.nodesource.com/setup_5.x | bash -
apt-get install -qq -y build-essential python-pip python-dev nodejs

function vagrant_exec() {
    sudo su -c "$1" vagrant -s /bin/bash
}

function home_exec() {
    vagrant_exec "(cd $CORVUS_HOME/corvus-web && $1)"
}

function setup_env() {
    pip install supervisor
    mkdir -p /etc/supervisord.d
    cp $CORVUS_VAGRANT/supervisord.conf /etc/supervisord.conf
    cp $CORVUS_VAGRANT/supervisord_upstart.conf /etc/init/supervisord.conf
    service supervisord start

    vagrant_exec "echo 'prefix = ~/.node' >> ~/.npmrc"
    vagrant_exec "echo \"export PATH=$PATH:$CORVUS_HOME/.node/bin\" >> ~/.bashrc"
}

function install_redis() {
    mkdir -p /opt/redis
    mkdir -p /data/redis/cluster
    cd /opt/redis
    wget -N http://download.redis.io/releases/redis-3.0.3.tar.gz
    tar zxf redis-3.0.3.tar.gz
    cd redis-3.0.3
    make
    make PREFIX=/opt/redis install

    mkdir -p /etc/redis
    for i in {8000..8063}
    do
        sed "s/{{ port }}/$i/" $CORVUS_VAGRANT/redis.conf > /etc/redis/redis-cluster-$i.conf
        sed "s/{{ port }}/$i/" $CORVUS_VAGRANT/redis-cluster.ini > /etc/supervisord.d/redis-cluster-$i.ini
        supervisorctl update redis-cluster-$i
    done
}

function setup_corvus_web() {
    pip install virtualenv

    vagrant_exec "npm install -g bower gulp"
    vagrant_exec "virtualenv $CORVUS_HOME/corvus-web-env"
    home_exec "$CORVUS_HOME/corvus-web-env/bin/pip install -e ."
    home_exec "npm install"
    home_exec "$BOWER install"
    home_exec "$GULP"

    mkdir -p /var/log/corvus-web
    cp $CORVUS_VAGRANT/corvus-web.ini /etc/supervisord.d/corvus-web.ini
    supervisorctl update corvus-web corvus-agent
}


setup_env
install_redis
setup_corvus_web
