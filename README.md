# Annotations Backend

Annotations backend provides storage api for annotations in Catchpy WebAnnotation format.


# Vagrant Quick Start

this iwll start 2 ubuntu 16.04 instances: one for postgres other for catchpy
django app.

you will need

- ansible provisioning repo dir at the same level as catchpy dir
- vagrant with landrush plugin (for dns)
    - `vagrant plugin install landrush`
- virtualbox
- ansible

## step-by-step

    # clone catchpy and catchpy-provision
    git clone git@github.com:nmaekawa/catchpy.git
    git clone git@github.com:nmaekawa/catchpy-provision.git
    
    # start vagrant instances
    cd catchpy
    vagrant up
    
    # provision both instances
    ansible-playbook -i provision/hosts/vagrant.ini --private-key \
        ~/.vagrant.d/insecure_private_key provision/playbook.yml
        
    # now go to a browser and access http://catchpy.vm/static/anno/index.html
    # this will present a nice interface for the catchpy api
    # note that, for vagrant, nginx is configured to serve content via HTTP;
    # and in prod, via HTTPS.


## more info on provisioning

check readme from catchpy-provisioning repo at
https://github.com/nmaekawa/catchpy-provision
