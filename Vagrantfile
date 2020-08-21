# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  config.vm.synced_folder ".", "/mzcli"

  mzcli_version = ENV['version']
  mzcli_description = "Postgres CLI with autocompletion and syntax highlighting"

  config.vm.define "debian" do |debian|
    debian.vm.box = "chef/debian-7.8"
    debian.vm.provision "shell", inline: <<-SHELL
    echo "-> Building DEB on `lsb_release -s`"
    sudo apt-get update
    sudo apt-get install -y libpq-dev python-dev python-setuptools rubygems
    sudo easy_install pip
    sudo pip install virtualenv virtualenv-tools
    sudo gem install fpm
    echo "-> Cleaning up old workspace"
    rm -rf build
    mkdir -p build/usr/share
    virtualenv build/usr/share/mzcli
    build/usr/share/mzcli/bin/pip install -U pip distribute
    build/usr/share/mzcli/bin/pip uninstall -y distribute
    build/usr/share/mzcli/bin/pip install /mzcli

    echo "-> Cleaning Virtualenv"
    cd build/usr/share/mzcli
    virtualenv-tools --update-path /usr/share/mzcli > /dev/null
    cd /home/vagrant/

    echo "-> Removing compiled files"
    find build -iname '*.pyc' -delete
    find build -iname '*.pyo' -delete

    echo "-> Creating PgCLI deb"
    sudo fpm -t deb -s dir -C build -n mzcli -v #{mzcli_version} \
        -a all \
        -d libpq-dev \
        -d python-dev \
        -p /mzcli/ \
        --after-install /mzcli/post-install \
        --after-remove /mzcli/post-remove \
        --url https://github.com/dbcli/mzcli \
        --description "#{mzcli_description}" \
        --license 'BSD'
    SHELL
  end

  config.vm.define "centos" do |centos|
    centos.vm.box = "chef/centos-7.0"
    centos.vm.provision "shell", inline: <<-SHELL
    #!/bin/bash
    echo "-> Building RPM on `lsb_release -s`"
    sudo yum install -y rpm-build gcc ruby-devel postgresql-devel python-devel rubygems
    sudo easy_install pip
    sudo pip install virtualenv virtualenv-tools
    sudo gem install fpm
    echo "-> Cleaning up old workspace"
    rm -rf build
    mkdir -p build/usr/share
    virtualenv build/usr/share/mzcli
    build/usr/share/mzcli/bin/pip install -U pip distribute
    build/usr/share/mzcli/bin/pip uninstall -y distribute
    build/usr/share/mzcli/bin/pip install /mzcli

    echo "-> Cleaning Virtualenv"
    cd build/usr/share/mzcli
    virtualenv-tools --update-path /usr/share/mzcli > /dev/null
    cd /home/vagrant/

    echo "-> Removing compiled files"
    find build -iname '*.pyc' -delete
    find build -iname '*.pyo' -delete

    echo "-> Creating PgCLI RPM"
    echo $PATH
    sudo /usr/local/bin/fpm -t rpm -s dir -C build -n mzcli -v #{mzcli_version} \
        -a all \
        -d postgresql-devel \
        -d python-devel \
        -p /mzcli/ \
        --after-install /mzcli/post-install \
        --after-remove /mzcli/post-remove \
        --url https://github.com/dbcli/mzcli \
        --description "#{mzcli_description}" \
        --license 'BSD'
    SHELL
  end

end

