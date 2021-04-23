#!/usr/bin/python

DOCUMENTATION = '''
---
module: check_user
short_description: check_user module will verify the user and userid was created correctly or not
'''

EXAMPLES = '''
- name: Checking user name - user id are free to provision
  check_user:
    users: {"ndip5":1055, "ndip6":1006, "ndip7":1007, "ndip8":1008, "ndip8":1008}
  register: usercheck_result
'''



from ansible.module_utils.basic import *
import pwd, grp
import itertools
import logging, platform, os, socket

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler('ansible_change.log')
formatter    = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)



def checkgrpexist(data):
    checkgrp = {}
    groups = grp.getgrall()
    for group in groups:
        checkgrp[group[0]] = group[2]
    allgivengroup = {}
    grpvalidation = []
    groupdict = {}

    for (groupname,groupid) in zip(data.keys(),data.values()):
        sysgrpkey,sysgrpvalue = groupname,int(groupid)
        if sysgrpkey in checkgrp and sysgrpvalue == checkgrp[sysgrpkey]:
            print("Group exists with the correct group id")
            plog = "Group exist with the correct group id" + " --- Group Name: " + sysgrpkey + " Group ID: " + str(sysgrpvalue)
            logger.info(plog)
            meta = {"groupname": sysgrpkey, "groupid": sysgrpvalue, "Description": "Group exists with the correct group id, no further action", "validation": True}
            allgivengroup[sysgrpkey] = meta
            grpvalidation.append(True)
            #return False, False , meta
        elif sysgrpkey in checkgrp and sysgrpvalue != checkgrp[sysgrpkey]:
            print("group exists")
            plog = "Group exist but group id is not matching" + " --- Group Name: " + sysgrpkey + " Group ID: " + str(sysgrpvalue)
            logger.info(plog)
            meta = {"groupname": sysgrpkey, "groupid": sysgrpvalue, "Description": "Group exists but group id is not matching, no action taken", "validation": False}
            allgivengroup[sysgrpkey] = meta
            grpvalidation.append(False)
            #return False, False , meta
        elif sysgrpvalue in checkgrp.values():
            print("group sysadmin dint exist but gid already used by some other group")
            plog = "Group dint exist but group id is already used by someother group" + " --- Group Name: " + sysgrpkey + " Group ID: " + str(sysgrpvalue)
            logger.info(plog)
            meta = {"groupname": sysgrpkey, "groupid": sysgrpvalue, "Description": "Group does not exist but group id is already used by someother group, no action taken", "validation": False}
            allgivengroup[sysgrpkey] = meta
            grpvalidation.append(False)
        else:
            print("group sysadmin dint exist")
            plog = "group sysadmin dint exist and group id also available to create" + " --- Group Name: " + sysgrpkey + " Group ID: " + str(sysgrpvalue)
            logger.info(plog)
            meta = {"groupname": sysgrpkey, "groupid": sysgrpvalue, "Description": "Group and gid is do not exist - Group will be created", "validation": False}
            allgivengroup[sysgrpkey] = meta
            grpvalidation.append(False)
            #return False, False , meta
    if False in set(grpvalidation):
        validation = False
    else:
        validation = True
    return validation


def checkuserexist(data):
    checkuser = {}
    users = pwd.getpwall()
    for user in users:
        checkuser[user[0]] = user[2]
    allgivenuser = {}
    userdict = {}
    groupdict = {}
    create_userdetails = {} 
    expire_userdetails = {}
    remove_userdetails = {}
    for processuserdict in data['users']:
        userdict.update({processuserdict["uname"]:processuserdict["uid"]})
        secgroup = []
        if processuserdict["action"] == "add user":
            try:
                groupdict.update({processuserdict["gname"]:processuserdict["gid"]})
                if isinstance(processuserdict["secgroup"], list):
                    for secgroupname in processuserdict["secgroup"]:
                        secgroup.append(secgroupname["name"])
                        groupdict.update({secgroupname["name"]:secgroupname["sgid"]})
            except:
                secgroup = []

            usercreation = checkgrpexist(groupdict)
            create_userdetails.update({processuserdict["uname"]: [processuserdict["action"],usercreation,processuserdict["comment"],processuserdict["gname"],processuserdict["hmdir"],secgroup,processuserdict["shell"]]})
        elif processuserdict["action"] == "expire user":
            expire_userdetails.update({processuserdict["uname"]: [processuserdict["action"],False,processuserdict["comment"],processuserdict["hmdir"],processuserdict["shell"]]})
        elif processuserdict["action"] == "remove user":
            remove_userdetails.update({processuserdict["uname"]: [processuserdict["action"],False,processuserdict["comment"],processuserdict["hmdir"],processuserdict["shell"]]})
        else:
            print("None of the actions matching")
    #userdict = data['users']
    for (username,userid) in zip(userdict.keys(),userdict.values()):
        usernamekey,useridvalue = username,int(userid)
        if usernamekey in checkuser and useridvalue == checkuser[usernamekey]:
            print("User already created with respective correct userid")
            plog = "User already created with respective correct userid " + " --- User Name: " + usernamekey + " User ID: " + str(useridvalue)
            logger.info(plog)
            if usernamekey in expire_userdetails.keys():
                meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": True, "Remove": False, "Description": "Expire User: User account successfully expired"}
            elif usernamekey in remove_userdetails.keys():
                meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": False, "Remove": True, "Description": "Remove User: User and home directory successfully removed"}
            else:
                meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": False, "Remove": False, "Description": "User already created with respective correct userid"}
            allgivenuser[username] = meta
            #return False, False , meta
        elif usernamekey in checkuser and useridvalue != checkuser[usernamekey]:
            print("User already created but with wrong userid")
            plog = "User already created but with wrong userid" + " --- User Name: " + usernamekey + " User ID: " + str(useridvalue)
            logger.info(plog)
            meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": False, "Remove": False, "Description": "User already created but with wrong userid, no action taken"}
            allgivenuser[username] = meta
            #return False, False , meta
        elif useridvalue in checkuser.values():
            print("Userid already used by different user")
            plog = "Userid already used by different user" + " --- User Name: " + usernamekey + " User ID: " + str(useridvalue)
            logger.info(plog)
            meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": False, "Remove": False, "Description": "Userid already used by different user, no action taken"} 
            allgivenuser[username] = meta
            #return False, False , meta
        else:
            print("User is not created")
            plog = "User is not created" + " --- User Name: " + usernamekey + " User ID: " + str(useridvalue)
            logger.info(plog)
            if usernamekey in create_userdetails.keys():
                meta = {"username": usernamekey, "userid": useridvalue, "Create": True, "Expire": False, "Remove": False, "Description": "Add User: User name and id are free to provision, user successfully created"} 
            else:
                meta = {"username": usernamekey, "userid": useridvalue, "Create": False, "Expire": False, "Remove": False, "Description": "Cannot Remove or Expire user since Username or UID do not exist is system"} 
            allgivenuser[username] = meta
            #return False, False , meta
    return False, False, allgivenuser, userdict, create_userdetails, expire_userdetails, remove_userdetails

def main():
    fields = {"users": {"required": True, "type": "list"},
              "state": {
        	"default": "present", 
        	"choices": ['present', 'absent'],  
        	"type": 'str' 
              },
    }
    choice_map = {
      "present": checkuserexist,
    }
    module = AnsibleModule(argument_spec=fields)
    is_error, has_changed, result, userdict, create_userdetails, expire_userdetails, remove_userdetails = choice_map.get(module.params['state'])(module.params)
    if not is_error:
        module.exit_json(changed=has_changed, meta=result, userdict=userdict, create_userdetails=create_userdetails, expire_userdetails=expire_userdetails, remove_userdetails=remove_userdetails )
    else:
        module.fail_json(msg="Provided user name or user id is already used on servers /etc/passwd", meta=result, userdict=userdict, userdetails=userdetails,expire_userdetails=expire_userdetails, remove_userdetails=remove_userdetails)
    

if __name__ == '__main__':
    main()
