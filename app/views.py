import os
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from PIL import Image
import fal_client
import asyncio

def index(request):
    return render(request, 'index.html')

async def generateVideo(prompt, url):

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print("in progress ---- ",log["message"])

    result = await fal_client.subscribe_async(
                "fal-ai/kling-video/v1.5/pro/image-to-video",
                arguments={
                    "prompt": prompt,
                    "image_url": url,
                    "duration": "5",
                    "aspect_ratio": "16:9"
                },
                with_logs=True,
                on_queue_update=on_queue_update,
            )
    return result

def upload_file(request):
    print("request.methon --> ", request.method)
    print("request.FILES --> ", request.FILES)
    if request.method == 'POST' and request.FILES:
        form_type = request.POST.get('form_type')
        print(form_type)
        try:
            # Ensure the uploads directory exists
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            newImage = Image.new("RGB", (1600, 1280), "white")

            for index, (file_key, uploaded_file) in enumerate(request.FILES.items()):
                # Save the uploaded file
                file_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)
                temp_path = os.path.join(settings.MEDIA_ROOT, file_path)
                with Image.open(temp_path) as img:
                    img = img.resize((800, 1280))
                    newImage.paste(img, (index * 800, 0))
                os.remove(temp_path)

            combined_file = "combined.png"
            processed_file_path = os.path.join(upload_dir, combined_file)
            newImage.save(processed_file_path, "png")
            file_url = f"https://{request.get_host()}{settings.MEDIA_URL}uploads/" + combined_file
            print(file_url)
            if form_type=="form1":
                prompt = "Two people hug each other warmly.They are smiling. Replace background with romantic image."
            if form_type=="form2":
                prompt = "Two people kiss passionately. Replace background with romantic image."
            #Send file URLs to the special API
            #result = asyncio.run(generateVideo(prompt, file_url))
            #print(result)
            #Return success response
            return JsonResponse({
                'message': "fail",
                'file_urls': "result",
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)