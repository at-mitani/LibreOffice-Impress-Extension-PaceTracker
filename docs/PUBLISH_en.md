# Presentation Pace Tracker – Publishing on extensions.libreoffice.org

Site: https://extensions.libreoffice.org/
Official guide: [Using this site as an extension maintainer](https://extensions.libreoffice.org/en/home/using-this-site-as-an-extension-maintainer)

> The site's pages and field names may change. If anything here differs from the official guide, follow the official guide.

---

## 1. Before publishing

### 1.1 Check the metadata (`src/description.xml`)

| Item | Current value | What to check |
|---|---|---|
| `identifier` | `jp.atmitani.impress.pacetracker` | **Cannot be changed after publishing** (LibreOffice uses it to detect updates). Use a unique reverse-domain name. If you change it, also change `EXTENSION_ID` in `src/pacetracker.py` and the `service:` URLs in `src/Addons.xcu` |
| `version` | `1.0.0` | Increase it for every release (for example 1.0.1, 1.1.0) |
| `publisher` | `at.mitani` (links to the extensions site) | Set your public name and your homepage or source repository URL |
| `LibreOffice-minimal-version` | 7.4 | Only lower it after testing with that older version |
| License | Mozilla Public License 2.0, the same as LibreOffice (`src/registration/license.txt`, `LICENSE`) | Enter the same license on the site. Every source file starts with the MPL 2.0 notice (Exhibit A); keep it in new files too |

`description.xml` must start with `<?xml ...?>` on the very first character. Any space or line before it makes the installation fail ("XML declaration allowed only at the start of the document").

### 1.2 Build and test

```
python tools/build_oxt.py
```

This creates `dist/PresentationPaceTracker-<version>.oxt`. Before publishing, check the following with a clean user profile:

- [ ] It installs from the Extension Manager and the license is shown
- [ ] **Tools > Add-Ons > Presentation Pace Tracker** opens the settings dialog
- [ ] Start → the progress band appears at the bottom of the slide show and the turtle and rabbit move
- [ ] Going back to an earlier slide moves only the rabbit back
- [ ] Reset moves both icons back to the start
- [ ] Upload and Default work for all four icons (time, slide, start, goal)
- [ ] With Show on = Presenter Console only, the band appears only on the Presenter Console and not on the slides (test with two displays)
- [ ] With a single display and Presenter Console only, the band is not shown anywhere and the state line explains why
- [ ] Display area changes are applied and kept after Reset
- [ ] Switching **Language** between Auto, 日本語 and English works and no text is cut off
- [ ] With **Auto**, the dialog language matches a Japanese and an English LibreOffice user interface
- [ ] If possible, also test on Linux and macOS (the package is registered for `platform="all"`)

To test with a clean profile, start LibreOffice with a separate profile folder. On Windows keep the folder path short, because a long path can make the installation fail (Windows path length limit):

```powershell
& "C:\Program Files\LibreOffice\program\soffice.exe" "-env:UserInstallation=file:///C:/lotest"
```

### 1.3 Material for the listing

| Material | File |
|---|---|
| Logo | `src/icons/logo.png` (128×128) |
| Screenshots | `docs/images/screenshot_overlay.png` (progress band), `docs/images/screenshot_presenter.png` (on the Presenter Console), `docs/images/screenshot_dialog_en.png` (dialog, English), `docs/images/screenshot_dialog.png` (dialog, Japanese) |
| Description (English) | Based on `src/description/desc_en.txt` |
| Description (Japanese) | Based on `src/description/desc_ja.txt` |
| User guide | `docs/INSTALL_en.md`, `docs/INSTALL_ja.md` (put them on your homepage or repository and link to them) |
| Source code URL | If the code is on GitHub or similar, enter it in the homepage / repository field |

Example description:

> **Presentation Pace Tracker** shows a progress band at the bottom of the running Impress slide show. A turtle moves with the elapsed time and a rabbit moves with the slide progress, from a start flag to a goal flag. If the rabbit is ahead of the turtle you will finish on time. Set the planned duration, start/reset the measurement, adjust the position and size of the band and upload your own icons from *Tools > Add-Ons > Presentation Pace Tracker*. The settings dialog is available in English and Japanese.

## 2. Create an account

1. Create a TDF single sign-on (SSO) account at https://user.documentfoundation.org/.
2. Log in at https://extensions.libreoffice.org/admin with that account.

## 3. Create the extension entry

1. Select **English** in the language selector on the left (English is the main language and the fallback for all other languages).
2. Click the green **Add Extension** button.
3. Fill in the fields:
   - Title: `Presentation Pace Tracker`
   - Description: the English description from 1.3
   - Tags: a few that fit, such as `Impress`, `presentation`, `timer`
   - Homepage / source repository URL
   - Logo and screenshots (optional, but they make the extension easier to find)
   - License: `MPL-2.0` (Mozilla Public License 2.0, same as `license.txt`)
4. Click **create** to save. **Files can only be added after the entry has been saved.**

## 4. Add a release (.oxt)

1. Scroll down on your entry and click **Add Extension Release** in the releases section.
2. Fill in the form and click **Create**. Typically:
   - Version: `1.0.0` (same as `description.xml`)
   - Compatible LibreOffice versions: the versions you tested (for example 26.8 and any older version you checked)
   - Operating systems: the ones you tested (the extension is pure Python and is designed to run on any OS)
   - File: `dist/PresentationPaceTracker-1.0.0.oxt`
   - Release notes: for example `Initial release.`
3. Fill in the form as shown on the site (the official guide does not describe every field).

## 5. Add a Japanese description (optional)

1. Switch the language selector on the left to **日本語** (Japanese).
2. Translate only the fields marked with the purple two-letter icon. All other fields are shared between languages, so changing them here also changes the English page.
3. Label colors: green = English original, grey = English used as fallback, purple = translation saved. Tags are translated by the moderators.

## 6. Submit for publication

1. Click **publish**.
2. A volunteer moderator reviews the entry before it becomes public. There is no fixed review time.
3. Entries left in the private state are not in the review queue, so make sure to publish.
4. For questions, use the [Extensions category of the community forum](https://community.documentfoundation.org/c/extensions/36).

## 7. Publishing a new version

1. Increase `version` in `src/description.xml` (for example `1.1.0`).
2. Rebuild with `python tools/build_oxt.py` and test.
3. On your extension entry, add the new .oxt with **Add Extension Release** and publish again.
4. If there has been no release for more than a year, the site marks the extension as outdated. After testing with a new LibreOffice version, add that version to the compatibility list of the release and publish it again to remove the mark.

## 8. Contents of the package

```
PresentationPaceTracker-1.0.0.oxt
├── META-INF/manifest.xml      registers the Python component and the menu definition
├── description.xml            ID, version, name, license, minimum LibreOffice version
├── description/desc_en.txt, desc_ja.txt
├── registration/license.txt   Mozilla Public License 2.0 (shown when installing)
├── Addons.xcu                 Tools > Add-Ons menu and toolbar button
├── pacetracker.py             the extension (settings dialog, measurement, progress band)
└── icons/                     turtle, rabbit and flag icons, logo, toolbar icons
```
