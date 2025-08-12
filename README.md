# 🧠 [AlwaysSaved Extractor Service](https://github.com/jaimemendozadev/alwayssaved-extractor-service)

Welcome to the **AlwaysSaved** Extractor Service — the user-facing web app that powers your private, searchable knowledge base for long-form media. Built to deliver fast, intelligent, and intuitive experiences, this interface lets users upload, explore, and query their personal content with ease.

This is the repository for the Extractor Service - Step 3 of the [App Flow](#alwayssaved-system-design--app-flow) and the real start of the AlwaysSaved ML/AI Pipeline.


For more information about What is AlwaysSaved and its Key Features, refer to the [AlwaysSaved Frontend README](https://github.com/jaimemendozadev/alwayssaved-fe-app).

---

## Table of Contents (TOC)
- [Starting the App](#starting-the-app)
- [File Structure and Service Flow](#file-structure-and-service-flow)
- [AlwaysSaved System Design / App Flow](#alwayssaved-system-design--app-flow)

---
## Starting the App

We need to use a virtual environment (we use the [Pipenv virtualenv management tool](https://pipenv.pypa.io/en/latest/)) to run the app.

Navigate to the root of the project folder in your computer. Open 2 separate terminal windows that both point to the root of the project. In one of those terminal windows run the following commands:


Create and enter the virtual environment:
```
$ pipenv --python 3.11

```


Enter the virtual environment:

```
$ pipenv shell
```

Install the dependencies in the `Pipfile`:

```
$ pipenv install
```


Start the Extractor Service at the root `service.py` file:

```
$ python3 service.py
```




[Back to TOC](#table-of-contents-toc)

---
## File Structure and Service Flow

```
/
|
|___/services
|    |
|    |__/audio_extractor
|    |
|    |__/audio_transcription
|    |
|    |__/aws
|    | |
|    | |__s3.py
|    | |
|    | |__sqs.py
|    | |
|    | |__ssm.py
|    |
|    |
|    |
|    |__/utils
|      |
|      |__/mongodb
|      |
|      |__/types
|
|
|
|__service.py


```

So basically the AlwaysSaved ML/AI Pipeline starts here in the `Extractor Service` in concert with the `Extractor Queue` (see [Steps 2-3 of System Design Diagram](#alwayssaved-system-design--app-flow)).


But first, a little explanation on the [Data Entities of AlwaysSaved](https://github.com/jaimemendozadev/alwayssaved-fe-app/tree/main/utils/mongodb/schemamodels) and how incoming requests to the `Extractor Service` arrive from the Frontend.

On the Frontend for v1, Users can upload a single or multiple .mp4 Video `File`(s) to s3. When a single or multiple `Files` are uploaded to s3, the Frontend creates `File` MongoDB documents for each `File` upload.

Those newly created media `File` upload(s) are organized in a newly created MongoDB `"Note"` document.

When the `File` upload(s) to s3 finish, the Frontend sends an SQS Message Payload to the `Extractor Queue` that gets processed by the `Extractor Service`. The incoming SQS Message to the `Extractor Service` has the following shape:

```
[
  {
    user_id: string;
    media_uploads: [
      {
       note_id: ObjectID;
       user_id: ObjectID;
       s3_key: string;
      }
    ]
  }
]

```


Then for each SQS Message, for each `media_upload` in the Message Payload, the `Extractor Serviced` will:
  - Download the .mp4 media `File` from s3;
  - Extract the .mp3 audio file from the video;
  - Use the Whisper Model to transcribe the audio and create a .txt file of the transcript;
  - Upload the .txt transcript to s3; and
  - Send an outgoing SQS Message to the `Embedding Queue` [Step 4 of System Design Diagram](#alwayssaved-system-design--app-flow) with the following shape:


```
  {
      note_id: string;
      file_id: string;
      user_id: string;
      transcript_s3_key: string;
  }
```


[Back to TOC](#table-of-contents-toc)

---



## AlwaysSaved System Design / App Flow

<img src="https://raw.githubusercontent.com/jaimemendozadev/alwayssaved-fe-app/refs/heads/main/README/alwayssaved-system-design.png" alt="Screenshot of AlwaysSaved System Design and App Flow" />

Above 👆🏽you will see the entire System Design and App Flow for Always Saved.

If you need a better view of the entire screenshot, feel free to [download the Excalidraw File](https://github.com/jaimemendozadev/alwayssaved-fe-app/blob/main/README/alwayssaved-system-design.excalidraw) and view the System Design document in <a href="https://excalidraw.com/" target="_blank">Excalidraw</a>.


[Back to TOC](#table-of-contents-toc)

---

## Created By

**Jaime Mendoza**
[https://github.com/jaimemendozadev](https://github.com/jaimemendozadev)
