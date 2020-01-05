#!/bin/zsh
#기존zip파일 삭제하고
rm *.zip
#다시 zip을하는데 배스트 트랙의 집을한다 
zip facebook_app.zip -r *

# 기존의 압축을 지우고
aws s3 rm s3://spotify-lambda-app/facebook_app.zip 

# 로컬 압축을 s3에 저장
aws s3 cp ./facebook_app.zip  s3://spotify-lambda-app/facebook_app.zip 

# 코드를  업데이트를                            람다 함수 이름 지정하고  존재하는 버킷이름 지정 , s3키는 압축파일이름
aws lambda update-function-code --function-name facebook_app --s3-bucket spotify-lambda-app --s3-key facebook_app.zip
