set -e
rm -rf pythonlibs-layer.zip exit 0
rm -rf python/ exit 0
docker run -v "$PWD":/var/task "lambci/lambda:build-python3.7" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.7/site-packages/; exit"
chmod 777 python/
zip -r pythonlibs-layer.zip python > /dev/null
rm -rf python/
