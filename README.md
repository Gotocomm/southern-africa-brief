# The Southern Africa Brief

A weekday podcast from Namela Development Institute that runs itself.

## How it works

1. **06:13 each weekday:** a Claude scheduled task researches the day's news on education, skills, gender equality and digital inclusion. It writes the script and saves it here as `episodes/YYYY-MM-DD.md`. It also saves a readable copy as a Claude Doc.
2. **A few minutes later:** GitHub turns the script into audio with a South African voice (Microsoft's "Leah"), adds it to the podcast feed and updates the website.
3. **Listeners** get the new episode in any podcast app that follows the feed.

Monday's episode is longer (about 10 minutes); Tuesday to Friday are about 5 minutes.

## Addresses

- Website: https://gotocomm.github.io/southern-africa-brief/
- Podcast feed (give this to Spotify, Apple Podcasts and others): https://gotocomm.github.io/southern-africa-brief/feed.xml

## Things you can change

All in `podcast.json`:

- `voice`: `en-ZA-LeahNeural` (female) or `en-ZA-LukeNeural` (male).
- `voice_rate`: speed, for example `-5%` for slower.
- `auto_publish`: set to `false` if you want to approve each episode first. Then an episode goes out only after you change its `status:` line to `approved`.
- `owner_email`: Spotify sends its verification code to this address.

To hold back one episode, change `status: publish` to `status: draft` in its file.

## If something goes wrong

- **No episode today:** check the scheduled task's run in Claude, then the **Actions** tab here. GitHub emails you when the audio step fails.
- **The voice sounds different:** the free Microsoft voice is not an official service. If it stops working, the build switches automatically to a free Google voice with a South African accent, and says so in the Actions log.
- **Storage:** each episode is about 2 MB. GitHub's limit is about 1 GB, so roughly two years of episodes. Older audio can be moved out before then.

## Files

- `episodes/`: the scripts, one per day.
- `site/audio/`: the audio files (made automatically).
- `tools/build.py`: makes the audio, the feed and the web page.
- `.github/workflows/publish.yml`: runs the build when a new script arrives.
- `cover.jpg`: the podcast artwork (1400 by 1400 pixels).
