# image-pack

This is a simple packing tool for android project ,specially, in selinux/sepolicy updating,system.img/userdata.img is time comsuming once making as AOSP build script.

You can utilize this tool to dev quickly or just for image build .

Note that it's best to lunch android source code firstly and take command with this script.
Usage:

1. python packimg.py --image [boot/recovery] -s --extras_image [system/data]
2. python packimg.py -s 
