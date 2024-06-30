run:
	sudo docker run --name testsite -d -p 8000:5000 --rm -e SECRET_KEY='150ce8e0c7df5b4797e90fdaa23c715171529b20' \
	--network testsite-network \
	-e DATABASE_URL=mysql+pymysql://test:1337@mysql/test \
	-e ELASTICSEARCH_URL=http://localgost:9200 \
    testsite:latest



stop:
	sudo docker stop testsite