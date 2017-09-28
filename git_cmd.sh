NEWDATE=$(date "+%H:%M:%S   %d/%m/%y")
git init
git add *
git commit -a -m "Adaptive Sampling $NEWDATE"
git remote add origin https://github.com/EnviroSCALE/pi_adaptive.git
git push -f -u origin master
