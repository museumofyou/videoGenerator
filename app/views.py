import os
import asyncio
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.core.files.storage import default_storage
from django.conf import settings
from PIL import Image, UnidentifiedImageError
import fal_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Index view
def index(request):
    return render(request, 'index.html')

# Asynchronous function to generate video
async def generate_video(prompt, url):
    async def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                logger.info(f"In progress: {log['message']}")

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

# File upload handler
def upload_file(request):
    if request.method == 'POST' and request.FILES:
        form_type = request.POST.get('form_type')
        if form_type not in ['form1', 'form2']:
            return JsonResponse({"error": "Invalid form type"}, status=400)

        try:
            # Ensure uploads directory exists
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            # Combine uploaded images
            new_image = Image.new("RGB", (1600, 1280), "white")
            for index, (file_key, uploaded_file) in enumerate(request.FILES.items()):
                try:
                    # Save the uploaded file
                    file_path = default_storage.save(f"uploads/{uploaded_file.name}", uploaded_file)
                    temp_path = os.path.join(settings.MEDIA_ROOT, file_path)

                    # Open, resize, and paste the image
                    with Image.open(temp_path) as img:
                        img = img.resize((800, 1280))
                        new_image.paste(img, (index * 800, 0))
                    
                    # Remove temporary file after processing
                    os.remove(temp_path)
                except UnidentifiedImageError:
                    return JsonResponse({"error": f"Invalid image file: {uploaded_file.name}"}, status=400)

            # Save the combined image
            combined_file = "combined.png"
            processed_file_path = os.path.join(upload_dir, combined_file)
            new_image.save(processed_file_path, "PNG")
            file_url = f"https://{request.get_host()}{settings.MEDIA_URL}uploads/{combined_file}"

            # Define prompt based on form type
            if form_type == "form1":
                prompt = "Two people hug each other warmly. They are smiling. Replace background with a romantic image."
            elif form_type == "form2":
                prompt = "Two people kiss passionately. Replace background with a romantic image."

            # Start video generation task
            async def process_video():
                result = await generate_video(prompt, file_url)
                logger.info(f"Video generation result: {result}")
                return result
            
            video_task = asyncio.create_task(process_video())
            result = asyncio.run(video_task)

            return JsonResponse({
                'message': 'Files uploaded and video generated successfully',
                'video_result': result,
            })

        except Exception as e:
            logger.error(f"Error during processing: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)