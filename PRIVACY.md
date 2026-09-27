# Privacy Policy

_Last updated: 2026-09-27_

This page is the privacy policy for the personal Google OAuth application
run by the maintainer of this repository ("HA Drive uploader"). The
application is used by a private Home Assistant installation to save
locally generated files (images and audio) into the maintainer's own
Google Drive.

## What the application does

- It requests the `https://www.googleapis.com/auth/drive.file` scope,
  which only allows it to create and manage files it has created itself.
  It cannot read, list or modify any other file in the Drive account.
- It uploads files from the maintainer's own Home Assistant server to
  folders in the maintainer's own Google Drive.

## Data collection and sharing

- The application is used only by its maintainer. It is not offered to,
  and does not collect data from, any other person.
- No personal data is collected, stored, sold or shared with any third
  party. OAuth tokens are stored only on the maintainer's private server.
- No analytics, advertising or tracking of any kind is involved.

## The integration in this repository

The Home Assistant integration in this repository (SMHI ODP) is unrelated
to the Google application above. It fetches public weather data from the
Swedish Meteorological and Hydrological Institute and stores nothing
outside the user's own Home Assistant instance.

## Contact

Questions can be raised as an issue in this repository.
