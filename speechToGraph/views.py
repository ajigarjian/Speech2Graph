import json
import whisper
import os
import re

from django.shortcuts import render
from django.urls import reverse
from django.http import JsonResponse
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from pydub import AudioSegment
from pyannote.audio import Pipeline
from transformers import pipeline
from pyannote.core import Annotation

import urllib.request

# preload whisper model
model = whisper.load_model("tiny.en")

# preload huggingface sentiment analysis pipeline to use on text transcribed from whisper model. Use default model and tokenizer
analyzer = pipeline("sentiment-analysis")

# preload pyannote.audio speaker-diarization pipeline to identify speakers
spacermilli = 2000
spacer = AudioSegment.silent(duration=spacermilli)
pipeline = Pipeline.from_pretrained('pyannote/speaker-diarization', use_auth_token="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")

audio = AudioSegment.from_wav('/Users/ajigarjian/Desktop/Speech2Graph/speech2graph/speechToGraph/static/YCS132.wav')
audio = spacer.append(audio, crossfade=0)
audio.export('output.wav', format='wav')

dz = pipeline('/Users/ajigarjian/Desktop/Speech2Graph/speech2graph/output.wav')  

with open("diarization.txt", "w") as text_file:
    text_file.write(str(dz))

print(*list(dz.itertracks(yield_label = True))[:10], sep="\n")

def millisec(timeStr):
  spl = timeStr.split(":")
  s = (int)((int(spl[0]) * 60 * 60 + int(spl[1]) * 60 + float(spl[2]) )* 1000)
  return s

dzs = open('diarization.txt').read().splitlines()

groups = []
g = []
lastend = 0

for d in dzs:   
  if g and (g[0].split()[-1] != d.split()[-1]):      #same speaker
    groups.append(g)
    g = []
  
  g.append(d)
  
  end = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=d)[1]
  end = millisec(end)
  if (lastend > end):       #segment engulfed by a previous segment
    groups.append(g)
    g = [] 
  else:
    lastend = end
if g:
  groups.append(g)
print(*groups, sep='\n')

audio = AudioSegment.from_wav("output.wav")
gidx = -1
for g in groups:
  start = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=g[0])[0]
  end = re.findall('[0-9]+:[0-9]+:[0-9]+\.[0-9]+', string=g[-1])[1]
  start = millisec(start) #- spacermilli
  end = millisec(end)  #- spacermilli
  print(start, end)
  gidx += 1
  audio[start:end].export(str(gidx) + '.wav', format='wav')

del pipeline, spacer,  audio, dz, newAudio
# Create your views here.

def index(request):
    return render(request, "./index.html")

@csrf_exempt
def transcribe(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)

    #Get audio file URI from POST
    data = json.loads(request.body)
    audio_uri = data.get("file")

    #Read the audio data in the audio file URI and store it into "data" variable
    with urllib.request.urlopen(audio_uri) as response:
        data = response.read()
    
    # create a new audio file "audio.wav" in static folder
    current_dir = os.path.dirname(__file__)
    rel_path = "static/audio.wav"
    abs_file_path = os.path.join(current_dir, rel_path)

    # Write audio content into new "audio.wav" file
    with open(abs_file_path, "wb") as f:
        f.write(data)

    # Transcribe audio.wav (with audio passed in from front end by user) in using whisper model
    result = model.transcribe(abs_file_path, fp16=False)

    res = analyzer(result["text"])
    label = res[0]['label']
    score = res[0]['score']

    return JsonResponse({
            "transcribed_text": result["text"],
            "text_label": label,
            "text_score": score
    }, safe=False)


def login_view(request):
    if request.method == "POST":

        # Attempt to sign user in
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        # Check if authentication successful
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "./login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "./login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]

        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "./register.html", {
                "message": "Passwords must match."
            })

        # Attempt to create new user
        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "./register.html", {
                "message": "Username already taken."
            })
        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "./register.html")
