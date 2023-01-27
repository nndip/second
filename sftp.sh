#!/bin/bash

export PATH=/ppb-bos/aws/bin:/bin:/sbin:/usr/sbin:/usr/bin
export PYTHONPATH=/ppb-bos/lib/pypi:\$PYTHONPATH


. /etc/sysconfig/arc-functions

positional=()
transfiles=()
failedfiles=()
is_debug="false"
lsof="/sbin/lsof"
date=$(date '+%m-%d-%Y')
filedropdir="/test/sftp/"
archivedir="/usace/sftp"
bucket="sftp-bucket"
lcenv=`get_lcenv`
lcorg=`get_lcorg`
lcidentity=`get_lcidentity`
isTransferred="false"
isEmail="true"
smtpTo="`get_ppbmail_to`"
smtpCc="`get_ppbmail_pki_team`"
smtpAppOwners="`get_ppbmail_appowners`"

### +-------------------------------------------------------------------------------------+ ###
### | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx H.E.L.P xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx | ###
### +-------------------------------------------------------------------------------------+ ###
function show_help() {
    basecmd=`basename $0`
    clear

    cat <<__HELP__
$(tput setaf 1)
### +-------------------------------------------------------------------------------+ ###
### | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx H.E.L.P xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx | ###
### +-------------------------------------------------------------------------------+ ###
$(tput sgr0)

`figlet "              *   PPB-BOS   *"`


$(tput setaf 2)[GFEBS Data Transfer]$(tput sgr0)
  ${basecmd}



$(tput setaf 3)[OPTIONS]$(tput sgr0)
  --debug: Run command in verbose mode

$(tput setaf 1)
### +-------------------------------------------------------------------------------+ ###
### | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx H.E.L.P xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx | ###
### +-------------------------------------------------------------------------------+ ###
$(tput sgr0)

__HELP__

    exit 0
}

while [ $# -gt 0 ]; do
    key="$1"
    case $key in
        --debug|-d)
            is_debug="true"
            shift
            ;;
        --help|-h)
            show_help
            shift
            ;;
        --bucket)
            bucket="$2"
            shift
            shift
            ;;
        *) positional+=("$1")
           shift
           ;;
    esac
done
set -- "${positional[@]}"

### +-------------------------------------------------------------------------------------+ ###
### | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx M.A.I.N xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx | ###
### +-------------------------------------------------------------------------------------+ ###
[ ${is_debug} = "true" ] && set -x

[ ! -x "${lsof}" ] && yum install lsof -y
[ ! -d "${archivedir}" ] && mkdir -p ${archivedir}

s3path="${bucket}/CAER/USACE/${date}"

while true; do
    isAllGood="true"
    for usace in `find ${filedropdir} -type f`; do
        ${lsof} ${usace} >/dev/null 2>&1

        if [ $? -eq 0 ]; then
            isAllGood="false"
        else
            usacebase=$(basename ${usace})
            aws s3 cp --quiet ${usace} s3://${s3path}/
            if [ $? -ne 0 ]; then
                logger_error "Failed to transfer ${usacebase} file to ${s3path}"
                failedfiles+=("${usacebase}")
            else
                isTransferred="true"
                transfiles+=("${usacebase}")
                rm -f ${usace}
                [ $? -ne 0 ] && \
                    logger_fatal "Failed to remove ${usace}"
            fi
        fi
    done

    if [ ${isAllGood} = "true" ]; then
        break
    else
        sleep 30
    fi
done

if [ ${isTransferred} = "true" ]; then
    isEmail="false"
    timestamp=$(date)
    elogfile="/tmp/ppbusace.log"
    truncate -s0 ${elogfile}

    exec > >(tee -i ${elogfile})
    exec 2>&1

    if [ ! -z "${transfiles}" ] ; then
        isEmail="true"
        echo "USACE File transfer:"
        for transfile in ${transfiles[@]}; do
            echo "    o ${transfile}"
        done
    fi

    echo ""

    if [ ! -z "${failedfiles}" ] ; then
        isEmail="true"
        echo "USACE File transfer failed:"
        for failedfile in ${failedfiles[@]}; do
            echo "    o ${failedfile}"
        done
    fi

    cat <<__INFO__


Timestamp  : ${timestamp}
S3 Bucket  : ${bucket}
S3 URI     : s3://${s3path}/
Environment: ${lcenv}
Identity   : ${lcidentity}

__INFO__

    if [ ${isEmail} = "true" ]; then
        subject="[USACE] File transfer notification"
         ppbmail \
             --to njock.ndip@ngc.com \
             --subject "${subject}" \
             --body-file ${elogfile}
        if [ -z "${smtpAppOwners}" ]; then
            ppbmail \
                ${smtpTo} \
                ${smtpCc} \
                --subject "${subject}" \
                --body-file ${elogfile}
        else
            ppbmail \
                ${smtpTo} \
                ${smtpCc} \
                ${smtpAppOwners} \
                --subject "${subject}" \
                --body-file ${elogfile}
        fi
    fi

    [ -f ${elogfile} ] && rm -f ${elogfile}
else
    logger_info "No files to transfer"
fi

exit 0

### +-------------------------------------------------------------------------------------+ ###
### | xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx E.N.D xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx | ###
### +-------------------------------------------------------------------------------------+ ###

