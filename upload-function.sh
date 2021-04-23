cd baseballCollectTweets
zip lambda.zip lambda_function.py
aws lambda update-function-code --function-name baseballCollectTweets --zip-file fileb://lambda.zip

cd ../baseballJanome
zip lambda.zip lambda_function.py
aws lambda update-function-code --function-name baseballJanome --zip-file fileb://lambda.zip

cd ../baseballCreateWordCloud
zip lambda.zip lambda_function.py stop_word.py
aws lambda update-function-code --function-name baseballCreateWordCloud --zip-file fileb://lambda.zip
