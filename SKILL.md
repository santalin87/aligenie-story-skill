# AliGenie story skill — let a child pick any episode by voice

Build a custom AliGenie skill that plays a specific episode of an audio
story series on a Tmall Genie speaker, with five-episode blocks for
continuous listening. One skill per series.

## This skill only works with an AI assistant

The procedure has too many fiddly steps to do by hand: episode-to-audio-ID
maps, Chinese-numeral parsing, five-episode merges, rename-to-pass review,
auth files, log checks. **Give this file to your AI assistant, give it one
goal (series, episode count, where the audio is, what to call it), and let
it run and test by itself — no need to check in at every step.** It should
only come back to you when it needs authorization: a sign-in verification,
a step only you can do, or anything that costs money. You verify at the end
by voice on the real speaker. The AI's job is everything else, including
correcting its own course when a test fails; your job is to set the goal,
give authorization when asked, and correct the direction when its first
diagnosis is wrong.

## Set up one skill per series

- Build one AliGenie custom skill for each audio series and keep each
  series in its own skill.
- Give each skill its own audio library, its own invocation word of six
  characters or fewer, and its own episode map on the backend.
- The invocation-word field takes exactly one word: a single input box
  (placeholder "请填写1-6个字的调用词"), no add-second-word control
  (verified 2026-11-13 on skill 121811 — "苗苗青衿之志" could not be
  added alongside "苗苗第三季").
- Keep series apart because two series would collide on the same phrase
  for episode one.
- Pick an invocation word the platform does not already claim and test it
  by voice before you build the library around it.
- Expect collisions with a singer name, a built-in trial skill, or a song
  title and change the word when the speaker answers with the wrong
  content.

## Put the backend on a server inside mainland China

- Run the backend on a server inside mainland China and reach it only by
  its IP address literal, never by a domain name.
- Treat an unfiled domain as blocked because the platform returns a 403
  page or cuts the connection at once.
- Do backend work on that server itself and bring data back through it,
  because a browser outside China hits platform risk checks on sign-in.
- Keep the backend address in IP form in every place the platform stores
  it, including the skill service address and any file the platform
  fetches for authentication.
- Serve the platform authentication file so a HEAD request for it returns
  200, because a 404 there fails the skill check before any voice test
  runs.
- Set the authentication file's permissions to 644 after copying it to
  the server, because a restrictive mode (600 from scp) makes nginx
  answer 403 and the service save fails even though the file exists.
- Check the backend log after each online test and treat a log with no
  new entry as proof the request never reached the backend.

## Build the audio library and episode map

- Upload episodes one by one when a single blocked file must not block
  the whole batch, and try the batch entry only after single uploads work.
- Use the '批量上传' button on the audio list toolbar for bulk uploads,
  but only with ASCII file names: the batch dialog rejects Chinese-named
  files with '暂不支持该文件类型' before they even enter its list
  (verified with byte-identical files — the same file passes under an
  ASCII name), while the single '+ 添加' form accepts Chinese names fine.
  In the batch dialog each row's name defaults to the file name without
  '.mp3' and is editable via the pencil icon; rename every row to the
  target material name, then one '保存' uploads the whole list.
- Fill in the author field on every batch upload: an empty author makes
  the whole batch fail silently — no error message, no record, the list
  looks as if nothing was ever uploaded. One consistent author name for
  the series is enough.
- Select all files in ONE multi-select when adding to the batch dialog: picking them in several rounds leaves some rows stuck at duration 00:00:00, and saving then fails with '添加失败，来源为空' — the whole batch is lost and the dialog draft is cleared. Wait until every row shows a parsed (non-zero) duration before renaming and saving.
- Write the batch import template with the episode slot written as
  @{集数}. A ready-made template is `corpus_import.csv` in this repo.
- After importing the corpus, open the intent edit page and click the blue
  '语音交互模型训练' button, because importing alone never trains the
  model. Until training is triggered and finishes, the online test matches
  no intent, calls no webhook, and answers '对不起，我暂时还不支持这项
  功能', while the wake word still enters the skill through the default
  intent and can mislead the diagnosis. Retest about fifteen minutes after
  triggering training and confirm the play request in the backend log
  before blaming the backend.
- Save intent examples as '例句' so the {集数} slot stays literal in the
  platform.
- Parse Chinese numerals in spoken episode phrases, so '五十一' becomes
  51 and '一七六七' becomes 1767. A reference implementation is in
  `backend/miao-skilld.py`.
- Keep the episode number and the platform audio ID apart, because an
  audio ID is not an episode number.
- Expand the backend episode map to the full series and spot check
  episodes across the range, including the last episode, before you
  report the series as live.
- Check the title's episode number first when an episode is rejected for
  a sensitive word, because the Arabic numerals 64 and 89 in a title trip
  the platform filter while the same audio passes under a range title or
  a Chinese numeral title.
- Rename a rejected episode with Chinese numerals for its number and a
  digit-free file name, then re-upload it and record the new audio ID
  before falling back to transcript hunts or split-half tests.
- Localise the hit by splitting the audio in half and re-uploading each
  half when the user wants the episode recovered, and mute only the
  segment that still blocks.
- Ask the user before a long split-half hunt, because each trial upload
  costs time and the user may prefer to leave the episode out and play it
  by another means.
- Report blocked episodes by number with the reason the platform gave,
  and keep the rest of the series live while one episode is blocked.

## Activate a new skill promptly and rebuild a skill whose wake never arrives

- Bind the real device and run the first voice test within the hour after
  building a skill, because one skill left unactivated for about a day
  never routed its wake to the backend at all, in the online tester or on
  the device, under two different invocation words, while two skills built
  and bound the same evening worked on the first try.
- Treat a wake phrase that never reaches the backend in the online tester
  as a broken skill, not a tester quirk, because healthy skills do POST
  their launch request there; when every console setting already matches
  a working skill, rebuild the series as a fresh skill instead of renaming
  again, which fixed both cases above.
- Free an invocation word for the rebuilt skill by renaming the broken
  skill's invocation word first; the platform then accepts the same word
  on the new skill with no conflict prompt.
- Expect pause and resume to bypass the skill entirely, because both are
  handled on the device and neither reaches the backend log; resuming
  after a pause falls back to the platform's own audio instead of the
  skill's stream, so tell the child to re-ask for the episode instead of
  pressing resume.

## Bind the real device and test by voice

- Turn the real device test switch on in the console and verify it stays
  on after a refresh, because a switch left off makes the speaker unable
  to find the skill at all.
- Expect the mode setting to resist saving and fall back to manual device
  binding when the direct device mode reverts on refresh.
- Bind the speaker with the voice verification code the user reads from
  the device and confirm the console reports the device added.
- Test by voice on the real speaker, not only in the console, and confirm
  the speaker enters the skill and plays the requested episode.
- Treat a correct voice recognition followed by a not-found answer as a
  test switch or binding problem before you blame the invocation word.
- Treat continuous playback as unproven, because the official protocol
  gives no queue and no play-finished callback and one reply returns one
  audio file.
- Fall back to concatenating audio on the server into one long file and
  re-uploading it when the multi-instruction probe fails. That is the
  five-episode block method used here: merge five adjacent episodes into
  one file, name it as a range (e.g. 第41到45集), and let the backend
  answer the block's first episode with the merged file.

## Audio sources

- Audio can come from a cloud drive download (e.g. Baidu Netdisk) or
  from files the user already downloaded and put on a drive the AI can
  read (e.g. Google Drive). Either way the files must land on the backend
  server first; without a server of your own to receive them, find one
  before starting.
- Probe downloaded files with ffprobe before merging, because a series
  can ship AAC audio in M4A containers renamed to .mp3, which stream-copy
  concatenation into an MP3 container rejects; transcode those to real
  MP3 (libmp3lame 64k) while concatenating the parts of each episode.

## Alternatives for better results

- Start a new series as a new skill instead of deleting the finished
  series, because deletion loses a working library the child still uses.
- Download the full series to the backend server before uploading, so a
  stalled upload resumes from local files instead of a fresh download.
- Keep the episode map and the library in step, and re-check the map
  after any re-upload that renumbers an episode.
- Offer the user the choice to leave a blocked episode out before you
  spend many trial uploads on it.

## Websites

- [AliGenie](https://aligenie.com/) for the custom skill console. Carry
  the skill name, the invocation word, and the backend IP address into
  the browser task and verify the skill saves, the test switch stays on,
  and the device list shows the bound speaker.
