#!/bin/bash

echo -n "Step: "
read step

if [$step == 1]; then
    sudo apt update && sudo apt full-upgrade
    sudo apt install imx500-all imx500-tools
    sudo apt install python3-opencv python3-munkres
    sudo reboot
elif [$step == 2]; then
    imx500-package -i packerOut.zip -o .
    cd ..
    git clone https://github.com/raspberrypi/picamera2
    cd picamera2
    pip install -e .  --break-system-packages
    cd examples/imx500
    python imx500_object_detection_demo.py --model ../spy-glass-pi/network.rpk --fps 25 --bbox-normalization --ignore-dash-labels --bbox-order xy --labels ../spy-glass-pi/labels.txt>
else
    echo "Invalid step"
fi
