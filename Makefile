setup:
	sudo apt updatesudo apt full-upgrade
	sudo apt install imx500-all imx500-tools
	sudo apt install python3-opencv python3-munkres
	sudo reboot
picamera:setup
	cd ~;\
	git clone https://github.com/raspberrypi/picamera2;\
	cd ~/picamera2;\
	pip install -e .  --break-system-packages
networkrpk:picamera
	imx500-package -i packerOut.zip -o .
run:networkrpk
	python demo.py --model network.rpk --fps 25 --bbox-normalization --ignore-dash-labels --bbox-order xy --labels labels.txt
all: setup picamera networkrpk
	echo "You spy glass model is ready!  Type `make run` to run a demonstration of it."
clean:
	rm -fr network.rpk
