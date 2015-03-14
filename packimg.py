#! /usr/bin/env python
#coding=utf-8

import sys, os
from optparse import OptionParser
import subprocess as sub 
import getopt
import re

def external_call(command, capture_output=True):
    print "Packing:\tRunning %s" % command
    errors = None
    output = None
    try:
        if capture_output:
            p = sub.Popen(command, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
            output, errors = p.communicate()
        else:
            output = os.system(command)
    except Exception, e:
        print "Packing: Error executing command '%s'. Reason: %s" % (str(command), e)
        #clean_up()
        sys.exit(1)
    finally:
        if (not errors is None) and (not errors == ""):
            print "Packing: Process stderr: %s" % errors
    return output

def search_file(filename):
    path = os.path.abspath(filename)
    if os.path.exists(path):
        print "Packimage:\tpath exists in:%s" % path
        return 0
    else:
        print "Packimage:\tpath not exist in:%s" %path
        return -1

def usage():
    print "Usage:python packimg.py --image [boot/recovery] -s --extras_image [system/data]"

def collect_files(project):
    """Load each BoardConfig.mk in the device dir
       which specifies with project"""
    files = []
    #extract specified device-name for configs collecting
    filename = "device/moto/"+project+"BoardConfig.mk"
    if search_file(filename) is not 0:
        return None
    files.append(filename)
    f = open(filename,'r')
    line = f.readline()
    while line:
        result = re.search("include",line)
        if result:
            config_file = str(line.strip('\n').split(' ')[1:])
            if search(config_file) is not 0:
                return None
            else:
                files.append(config_file)
        #next cycle with reading next line
        line = f.readline()
    print files
    return files

def collect_values(project,image):
    """Load "config=arg" pairs which may used as arguments for the image"""
    arg_dict = {}
    files = collect_files(project)
    if files is None:
       sys.exit(-1)
    if image is 'system':
        configs = {'system_image_size':None}
        for config_file in files:
            arg_dict = get_dict(config_file,'BOARD_SYSTEMIMAGE_PARTITION_SIZE')
            configs['system_image_size'] = arg_dict['BOARD_SYSTEMIMAGE_PARTITION_SIZE']
    if image is 'boot' or image is 'recovery':
        configs = {'cmdline':None,
                   'kernelbase':None,
                   'board_page_size':None,
                   'ramdisk_offset':None,
                   'tags_offset':None}
        for config_file in files:
            arg_dict = get_dict(config_file,'BOARD_KERNEL_CMDLINE')
            configs['cmdline']=arg_dict['BOARD_KERNEL_CMDLINE'] 

            arg_dict = get_dict(config_file,'BOARD_KERNEL_BASE')
            configs['kernelbase']=arg_dict['BOARD_KERNEL_BASE']

            arg_dict = get_dict(config_file,'BOARD_KERNEL_PAGESIZE')
            configs['board_page_size']=arg_dict['BOARD_KERNEL_PAGESIZE']

            arg_dict = get_dict(config_file,'BOARD_RAMDISK_OFFSET')
            configs['ramsdisk_offset']=arg_dict['BOARD_RAMDISK_OFFSET']

            arg_dict = get_dict(config_file,'BOARD_KERNEL_TAGS_OFFSET')
            configs['tags_offset']=arg_dict['BOARD_KERNEL_TAGS_OFFSET']            
    return configs

def get_dict(filename,keyword):
    """Load {key,value} used in each makefile specified in the device"""
    d = {}
    key = None
    value = None
    f = open(filename)
    for line in f:
        line = line.strip("\n")
        if line and re.search(keyword):
            stok = re.split(":=",line)
            value = stok[1:]
            key = re.split(" ",stok[0])[0]
            d[key] = value
        else:
            d[keyword] = None
    f.close()
    return d
 
def build_sepolicy(sepolicy = False):
    """Generate sepolicy file and other stuff like file_contexts for packing and labeling"""
    if sepolicy is False:
        print "Not need to generate sepolicy"
    else:
        try:
            external_call("mmm external/sepolicy")
        except Exception, e:
            print "Error:"
            print e
            sys.exit(-1)

def pack_ramdisk(product = None,image = None):
    """Generate ramdisk with host tool"""
    if product:
        cmd = ["out/host/linux-x86/mkbootfs"]
        if image is not None and image is 'boot':
            rootdir = "out/target/product/"+str(product)+"/recovery/root"
            output_image = "out/target/product/"+str(product)+"/ramdisk.img"
        elif image is not None and image is 'recovery':
            rootdir = "out/target/product/"+str(product)+"/root"
            output_image = "out/target/product/"+str(product)+"/ramdisk-recovery.img"
        else:
            print "Could not find ramdisk root dir"
            sys.exit(-1)
        minigzip = "out/host/linux-x86/bin/minigzip"
        cmd.extend([rootdir,minigzip,">",output_image])
        try:
            external_call(cmd)
        except Exception,e:
            sys.exit(-1)
     else:
        print "Could not pack ramdisk ,Please specify target root"
        
def pack_image(product = None,image = None):
    """Packing boot.img or recovery.img"""
    out_dir = "out/target/product/"+str(product)+"/"
    cmd = ["out/host/linux-x86/bin/mkbootimg"]
    cmd.append("--kernel")
    kernel = out_dir+kernel
    cmd.append(kernel)
    configs = collect_values(product,image)
    if image is not None:
        pack_ramdisk(product,image)
        if image is 'boot':
            ramdisk = out_dir+"ramdisk.img"
        elif image is 'recovery':
            ramdisk = out_dir+"ramdisk-recovery.img"
        cmd.append("--ramdisk")
        cmd.append(ramdisk)
        cmd.append("--cmdline")
        cmd.append(configs.get('cmdline'))
        cmd.append("--base")
        cmd.append(configs.get('kernelbase'))
        cmd.append("--pagesize")
        cmd.append(configs.get('board_page_size'))
        cmd.append("--ramdisk_offset")
        cmd.append(configs.get('ramdisk_offset'))
        cmd.append("--tags_offset")
        cmd.append(configs.get('tags_offset'))
        cmd.append("--dt")
        dt = out_dir+"dt.img"
        cmd.append(dt)
        cmd.append("--output")
        if image is 'boot':
            output_image = out_dir+"boot.image"
            cmd.append(output_image)
        elif image is 'recovery':
            output_image = out_dir+"recovery.img"
        else:
            print "image is not boot/recovery type"
        external_call(cmd)
    else:
        print "No boot/rec image to pack"
        
def pack_extras_image(product = None,extras_image = None):
    """Packing system.img with file_contexts"""
    out_dir = "out/target/product/"+str(product)+"/"
    cmd = ["out/host/linux-x86/bin/mkuserimg.sh"]
    configs = collect_values(product,extras_image)
    if configs.get('system_image_size') is None:
        sys.exit(-1)
    if extras_image is not None:
        cmd.append("-s")
        cmd.append(out_dir+"system")
        cmd.append(out_dir+"system.img")
        cmd.append("ext4")
        cmd.append("system")
        cmd.append(configs.get('system_image_size'))
        cmd.append(out_dir+"root/"+"file_contexts")
        external_call(cmd)
        #To do ,like sparse the image...
    else:
        print "No extras system image to pack"

def main():
    #set params
    parser = OptionParser()
    #set platform type
    parser.add_option('-p', '--project', action = 'store', type = 'string',dest = 'project', help = 'project,formatter: -p/--project z2t/aio_otfp/...')
    #set image type which need to package
    parser.add_option('-i', '--image', action = 'store', type = 'string', dest = 'image', help = 'image, formatter: -i/--image boot/recovery')
    #set flag for sepolicy compile
    parser.add_option('', '--sepolicy', action = 'store_true',default = False, dest = 'sepolicy',  help = 'Confirm sepolicy recompile, formatter: --sepolicy')
    #set flag for extras image building such as:system.img
    parser.add_option('-e', '--extras_image', action = 'store',type = 'string', dest = 'extras_image',  help = 'Confirm extras image packing, formatter: -e/--extras system')
    options, args = parser.parse_args()
    if options.project != None:
        if options.sepolicy is True:
            build_sepolicy(options.sepolicy)
        if options.image:
            pack_image(options.product,options.image)
        if options.extras_image:
            pack_image(options.project,options.extras_image)
    else:
        print "invaldid input and please follow the usage"
        usage()


if __name__ == '__main__':
    main()
