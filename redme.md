gcloud auth login
gcloud config set project my-innovation-project-419505
export PROJECT_ID=$(gcloud config get-value project)
echo $PROJECT_ID
Build your container image using Cloud Build:
gcloud builds submit --tag gcr.io/$PROJECT_ID/web-client-data-class

Deploy your image to Cloud Run:
gcloud run deploy web-client-data-class-svc --image gcr.io/$PROJECT_ID/web-client-data-class --platform managed --allow-unauthenticated

gcloud run deploy university-web-client-data-class-svc --image gcr.io/$PROJECT_ID/university-web-client-data-class --platform managed --allow-unauthenticated
![Uploading image.png…]()
