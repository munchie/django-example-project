Vagrant::Config.run do |config|
    config.vm.define :web1 do |config|
        config.vm.box = "precise64"
        config.vm.network :hostonly, "10.10.10.10"
        config.vm.forward_port 8000, 8000
        config.vm.host_name = "vagrant-web1"
        config.vm.customize ["modifyvm", :id, "--memory", 256]
    end

    config.vm.define :web2 do |config|
        config.vm.box = "precise64"
        config.vm.network :hostonly, "10.10.10.11"
        config.vm.forward_port 8000, 8080
        config.vm.host_name = "vagrant-web2"
        config.vm.customize ["modifyvm", :id, "--memory", 256]
    end

    config.vm.define :db1 do |config|
        config.vm.box = "precise64"
        config.vm.network :hostonly, "10.10.10.20"
        config.vm.forward_port 6379, 6379
        config.vm.forward_port 5432, 5432
        config.vm.host_name = "vagrant-db1"
        config.vm.customize ["modifyvm", :id, "--memory", 256]
    end
end