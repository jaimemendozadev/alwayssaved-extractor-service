# 🧠 [AlwaysSaved Extractor Service](https://github.com/jaimemendozadev/alwayssaved-extractor-service)

Welcome to the **AlwaysSaved** Extractor Service — the user-facing web app that powers your private, searchable knowledge base for long-form media. Built to deliver fast, intelligent, and intuitive experiences, this interface lets users upload, explore, and query their personal content with ease.

This is the repository for the Extractor Service - Step 3 of the [App Flow](#alwayssaved-system-design--app-flow) and the real start of the AlwaysSaved ML/AI Pipeline.

For more information about What is AlwaysSaved and its Key Features, refer to the [AlwaysSaved Frontend README](https://github.com/jaimemendozadev/alwayssaved-fe-app).

---

## Table of Contents (TOC)

- [3rd Party Services Needed](#3rd-party-services-needed)
- [Environment and AWS Systems Manager Parameter Store Variables](#environment-and-aws-systems-manager-parameter-store-variables)
- [Installing the App Dependencies](#installing-the-app-dependencies)
- [Starting the App](#starting-the-app)
- [File Structure and Service Flow](#file-structure-and-service-flow)
- [AlwaysSaved System Design / App Flow](#alwayssaved-system-design--app-flow)

---

## 3rd Party Services Needed

As a friendly reminder from the [AlwaysSaved Frontend](#https://github.com/jaimemendozadev/alwayssaved-fe-app), the following AWS Resources should have already been setup for this `Extractor Service` to work properly:

- An <a href="https://aws.amazon.com/s3/" target="_blank">s3 Bucket</a> with the right permissions for storing media files.
- Parameters stored in the <a href="https://aws.amazon.com/systems-manager/" target="_blank">AWS Systems Manager Parameter Store</a>.

<br />

An Amazon <a href = "https://aws.amazon.com/sqs/" target="_blank">Simple Queue Service</a> `Extractor Queue` was already created when you spun up the Frontend. You will now need to:

- Create a second SQS queue we call the `Embedding Queue` that the `Extractor Service` uses to send payloads to the `Embedding Service` to continue the next part of the ML/AI Pipeline (see [Steps 4-5 of System Design Diagram](#alwayssaved-system-design--app-flow)).

 <br />

Your newly created `Embedding Queue` URL will be saved in the AWS Parmeter Store ([see next section](#environment-and-aws-systems-manager-parameter-store-variables)).

<br />

[Back to TOC](#table-of-contents-toc)

---

## Environment and AWS Systems Manager Parameter Store Variables

You'll need to create a `.env` file at the root of this repo. There are only two variables that you have to prefill, which is the Region where all your AWS s3 Bucket and SQS Queues are located and if you're running the Python in a local or production enviroment.

```
AWS_REGION=

PYTHON_ENVIRONMENT=

```

<br />

`IMPORTANT`:

- The `.env` file gets copied into the final 🐳 Docker image. The only **IMPORTANT** variable that really needs to be set for production is the `PYTHON_ENVIRONMENT` variable set to `production`.

- In local development, if you set the `PYTHON_ENVIRONMENT` to `development` and you're running a MacBook with a GPU, it'll try to use the GPU to process the media files and audio transcription. Otherwise it defaults to the `cpu`.

<br />

For both development and production, there are a lot of variables that we couldn't store in the .env file, so we had to resort to using the <a href="https://aws.amazon.com/systems-manager/" target="_blank">AWS Systems Manager Parameter Store</a> ahead of time in order to get the app functioning.

The following variable keys have their values stored in the Parameter store as follows:

```
/alwayssaved/AWS_BUCKET

/alwayssaved/AWS_BUCKET_BASE_URL


/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL

/alwayssaved/EMBEDDING_PUSH_QUEUE_URL


/alwayssaved/MONGO_DB_USER

/alwayssaved/MONGO_DB_PASSWORD

/alwayssaved/MONGO_DB_BASE_URI

/alwayssaved/MONGO_DB_NAME

/alwayssaved/MONGO_DB_CLUSTER_NAME

```

If you already setup your MongoDB Cluster and s3 Bucket by setting up the [AlwaysSaved Frontend](#https://github.com/jaimemendozadev/alwayssaved-fe-app), adding those values in the AWS Parameter Store should be easy.

Make sure that the `Extractor Service` SQS URL gets saved in the paramter store under `/alwayssaved/EXTRACTOR_PUSH_QUEUE_URL` and the newly created `Embedding Queue` URL gets saved under `/alwayssaved/EMBEDDING_PUSH_QUEUE_URL`.

For clarification, your `AWS_BUCKET_BASE_URL` really means the URL that points to your Bucket in AWS like so:

```
https://<AWS_BUCKET_NAME>.s3.amazonaws.com

```

<br />

[Back to TOC](#table-of-contents-toc)

---

## Installing the App Dependencies

You'll need the <a href="https://docs.astral.sh/uv/" target="_blank">uv Python package/project manager</a> to start the app.

- If `uv` is not installed on your computer, <a href="https://docs.astral.sh/uv/getting-started/installation/" target="_blank">reference the documentation</a> for installation instructions.

The project also leverages the <a href="https://docs.astral.sh/ruff/" target="_blank">ruff Python linter/code formatter</a>.

- If `ruff` is not installed on your computer, <a href="https://docs.astral.sh/ruff/installation/" target="_blank">reference the documentation</a> for installation instructions.

The service uses <a href="https://ffmpeg.org/" target="_blank">FFmpeg</a> to extract audio from video files. You must have the FFmpeg binary installed on your system separately from the Python dependencies.

- On macOS, install via <a href="https://brew.sh/" target="_blank">Homebrew</a>:

```
$ brew install ffmpeg
```

- For other operating systems, <a href="https://ffmpeg.org/download.html" target="_blank">reference the FFmpeg download page</a> for installation instructions.

Once `uv`, `ruff`, and `ffmpeg` are installed, run the following command at the root of the repo to create the virtual environment and install all project and dev dependencies (including `pre-commit`):

```
$ uv sync
```

After `uv sync` completes, run the following command once to register the `pre-commit` git hooks:

```
$ pre-commit install
```

This wires up the `ruff` linter/formatter to run automatically whenever you commit changes.

<br />

[Back to TOC](#table-of-contents-toc)

---

## Starting the App

Once all the dependencies are installed and `pre-commit` hooks are registered (see [Installing the App Dependencies](#installing-the-app-dependencies)), open two separate terminal windows at the root of the repo.

**Terminal Window 1 — Run the service:**

```
$ uv run python service.py
```

This starts the Extractor Service and keeps it running.

**Terminal Window 2 — Development and Git commits:**

Enter the virtual environment that was created by `uv sync`:

```
$ source .venv/bin/activate
```

Use this terminal window during development to stage and commit your changes with Git. Because the `pre-commit` hooks are registered, any `git commit` will automatically run `ruff` to lint and format your code before the commit is saved.

If `ruff` finds errors, the commit will be blocked. Fix the reported issues, re-stage the files, and commit again. Once `ruff` passes, the commit will be saved and you can push the changes to GitHub.

To exit the virtual environment when you're done, run:

```
$ deactivate
```

<br />

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

On the Frontend for v1, Users can upload a single or multiple `.mp4` Video or `.mp3` Audio `File`(s) to s3. When the`File`(s) are uploaded to s3, the Frontend creates `File` MongoDB documents for each `File` upload.

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

<br />

Then for each SQS Message, for each `media_upload` in the Message Payload, the `Extractor Service` will:

- Download the media `File` from s3;
  - If the media download is an `.mp4` file, extract the `.mp3` audio file from the video;
- Use the [Whisper Model](https://openai.com/index/whisper/) to transcribe the audio and create a `.txt` file of the transcript;
- Upload the `.txt` transcript to s3; and
- Send an outgoing SQS Message to the `Embedding Queue` [Step 4 of System Design Diagram](#alwayssaved-system-design--app-flow) with the following shape:

```
  {
      original_filename: string;
      note_id: string;
      file_id: string;
      user_id: string;
      transcript_s3_key: string;
  }
```

The next part of the ML/AI Pipeline then moves on to the `Embedding Queue` and `Embedding Service` (see [Steps 4-5 of System Design Diagram](#alwayssaved-system-design--app-flow)).

<br />

[Back to TOC](#table-of-contents-toc)

---

## AlwaysSaved System Design / App Flow

<img src="https://raw.githubusercontent.com/jaimemendozadev/alwayssaved-fe-app/refs/heads/main/README/alwayssaved-system-design.png" alt="Screenshot of AlwaysSaved System Design and App Flow" />

Above 👆🏽you will see the entire System Design and App Flow for Always Saved.

If you need a better view of the entire screenshot, feel free to [download the Excalidraw File](https://github.com/jaimemendozadev/alwayssaved-fe-app/blob/main/README/alwayssaved-system-design.excalidraw) and view the System Design document in <a href="https://excalidraw.com/" target="_blank">Excalidraw</a>.

<br />

You can inspect the rest of the repos for each service/component in the diagram at the following URLs:

- [AlwaysSaved Frontend](https://github.com/jaimemendozadev/alwayssaved-fe-app)
- [Embedding Service](https://github.com/jaimemendozadev/alwayssaved-embedding-service)
- [LLM Service](https://github.com/jaimemendozadev/alwayssaved-llm-service)
- [Terraform Infra](https://github.com/jaimemendozadev/alwayssaved-terraform)

<br />

[Back to TOC](#table-of-contents-toc)

---

## Created By

**Jaime Mendoza**
[https://github.com/jaimemendozadev](https://github.com/jaimemendozadev)
