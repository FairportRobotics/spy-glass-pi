setup:
	sudo apt update
	sudo apt full-upgrade
	sudo apt install imx500-all imx500-tools
	sudo apt install python3-opencv python3-munkres
	@echo "You might need to restart the raspberry pi."
picamera:setup
	cd ~;\
	git clone https://github.com/raspberrypi/picamera2;\
	cd ~/picamera2;\
	pip install -e .  --break-system-packages
model:picamera
	imx500-package -i packerOut.zip -o .
reefscape:
	imx500-package -i reefscape.zip -o .
run:
	python demo.py --model network.rpk --fps 25 --bbox-normalization --ignore-dash-labels --bbox-order xy --labels labels.txt
all:model
	@echo "You spy glass model is ready!"
clean:
	rm -fr network.rpk
