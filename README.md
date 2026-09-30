# DSP Project Website

Public Dynamic System Policy research website: https://char1ie215.github.io/DSP_WEB/.
Plain HTML, CSS and JavaScript; no package manager or build step is required.
The page adapts the VisualForce website source at the user's request.
See `SOURCE.md` for provenance and the permission check required before release.

## Preview

Open `index.html` in a browser. All four tasks and their players work from a local file.
Alternatively, from this directory:

```powershell
py -m http.server 8000 --bind 127.0.0.1
```

Visit http://127.0.0.1:8000. Do not expose this server outside localhost.

## Files

- `index.html`: concise project overview, one method figure, field explanation, interactive recovery and experiment videos.
- `static/css/index.css`: original VisualForce stylesheet.
- `static/css/dsp.css`: DSP-specific responsive overrides.
- `static/js/project.js`: confirmed title, authors, affiliations, links and video paths.
- `static/js/results.js`: archived manuscript Tables I-IV and renderer; no longer loaded by the homepage.
- `static/js/index.js`: metadata rendering, four stacked task sections and per-task paired playback.
- `static/images/`: extracted original experimental frames and rendered figures.
- `static/figures/`: downloadable method figure PDFs, not the paper.
- `static/papers/paper.pdf`: unchanged copy of the supplied `Downloads/ICRA2027_DSP.pdf`, linked from Read the paper.
- `scripts/prepare_assets.py`: local asset extraction from original PPT/PDF sources.
- `asset_manifest.json`: task/frame file mapping.

The previous layout's `site.css` and `site.js` are not loaded by this page.
The complete previous draft is backed up outside this repository in
`Desktop/DSP_WEB_backup_before_reference_20260928_205207`.

## Add Confirmed Metadata and Videos

Edit `static/js/project.js`. Authors use `{name, affiliations, url}` entries;
affiliations use `{id, name}` entries. Blank lists and links stay hidden.
Set `teaser` to a local MP4 path. Each task accepts `success` and `failure` MP4
paths. All four tasks appear in sequence without tabs. One video uses a
single player; two videos enable paired playback controls for that task only.
Empty task sections stay hidden. Clips preload only when playback is requested.
Do not populate paths until the corresponding media files exist.

The full title and nine-author order follow the supplied submission screenshot.
Haoyu Chen's capitalization is normalized. The user explicitly confirmed equal
contribution for Cheng Zhu and Haonan Chen; both carry a star. The user confirmed
UPenn for Cheng Zhu, Jiayuan Mao and Nadia Figueroa; Harvard for Haonan Chen,
Feiyang Wu, Haoyu Chen and Yilun Du; UC San Diego for Yandong Ji.
The user explicitly confirmed UIUC for Yaqi Xie on this project. No corresponding
author designation has been supplied or inferred.

## Videos

The homepage player and Full video button both use the complete 168-second
`dsp-overview.mp4` presentation, unchanged. The player does not autoplay, mute
or loop the presentation. All four paired task-video sections remain below.

`static/videos/dsp-overview.mp4` is a byte-for-byte copy of the supplied
`Downloads/ICRA2027_DSP_video_under20MB.mp4` (168 seconds, about 17.4 MB).
The eight task videos were extracted from the matching local
`ICRA2027_DSP_video_template.pptx`, slides 11 (failure) and 12 (success).
Task identity was checked visually, not inferred from quadrant position:
the cola and drawer success clips occupy different quadrants from their failures.
Clips were remuxed with fast-start metadata, without cropping, trimming,
re-encoding, or changing their existing presentation speeds. They are individual
outcome examples, not baseline-versus-DSP comparisons.

`scripts/prepare_videos.py` reproduces extraction. `video_manifest.json` records
source entries, hashes, dimensions, and durations. Original files are unchanged.

## Draft Content and Provenance

### Interactive Recovery

The Interactive Recovery section is a synthetic, position-only kinematic
demonstration, not an online policy, robot simulation, or experimental result.
`scripts/prepare_recovery_demo.py` uses the existing implementation in
`Desktop/neural_symbolic_ds_method_a/src` to compile two preset ensembles:

- Original complete-link clustering, medoid selection, and transverse support statistics.
- Original locked-prefix Gaussian affine-field fitting for every integral command phase.
- Smooth-tube local CLF projection (paper Eq. 9), with a fixed measured-position reference and inverse regularized positional covariance at the accepted phase.

`static/js/recovery-data.js` stores the compiled parameters, reference outputs,
and SHA-256 hashes of the three source modules. `recovery-core.js` evaluates the
planar restriction in the browser, including stable softmax gating, smooth-tube CLF
projection, and direction-preserving magnitude limits. The fixed-step kinematic
integrator follows the repository's `animate_intervention.py` illustration.

Native motion uses ideal translation increments from the selected synthetic path;
there is no trained model or contact dynamics. During normal execution, every
position that passes the reliable current-segment support check updates the
accepted pose and phase. Pointer-down does not register a reference or pause
native execution; pointer motion adds a displacement to the moving point. A
current-segment support departure AND excessive command-relative innovation
trigger recovery and lock the latest accepted pose and its associated phase.
Outside states do not update this reference even if their innovation is below
threshold and native execution continues. Only recovery freezes command progress.
The pointer demo uses an innovation threshold of 0.0001 synthetic coordinate
units so a small transverse displacement across the tube boundary is enough to
activate the recovery visualization. This is not a robot-evaluation threshold;
support departure and innovation are still both required.
While recovering, holding the pointer imposes the displaced position; releasing
it allows recovery integration. Further drags during recovery do not change the
locked reference. Reentry requires two fixed
steps within 0.004 synthetic coordinate units of that reference. Orientation is
constant and gripper state is not modeled. A 30-second timeout is displayed rather
than silently snapping to the target.

After recovery, the next preset ensemble is translated to start its remaining
suffix at the recovered position. This is a synthetic replan, not inference.
The displayed phase is the index in the preset command sequence; during recovery
the readout shows the locked reference phase. A synthetic replan starts its new
suffix at that accepted phase, not at any later trigger phase. All thresholds,
trajectory scales and presentation timing are demonstration settings, not claims
about the numerical configuration of the paper's experiments. The green ribbon
shows transverse spread; membership is checked only on the current segment, not
the entire ribbon. The field shown during recovery comes only from the locked
prefix. The evaluator falls back to the source executor's reference feedback when
the prefix is empty.

Run `py scripts/check_recovery_demo.py` for numerical parity with all 588 exported
Python reference evaluations, 72 convergence cases (including translated measured
references), the smooth-tube descent inequality, accepted-state updates,
no premature locking on pointer-down, fixed phase/reference invariants, and
desktop/mobile pointer tests.
This test also checks keyboard interaction, pause/restart, canvas pixels and
responsive layout. Controls use locally stored Lucide icons; their license is
in `static/icons/LICENSE`.

Experimental images are extracted without raster editing from slide 1 of
`dsp_rollout.pptx` (three original frames per task). The middle Sweep Ball frame
shows repositioning, not the initial external push; its caption reflects this.
The homepage poster is a frame from the full project presentation.

The prediction and recovery figures use the user-supplied
`Downloads/dsp_method.pdf` and `Downloads/recovery.pdf`, updated on 2026-09-29.
The downloadable PDFs are unchanged copies; PNG previews are rendered from them.
Only the prediction figure is displayed on the simplified homepage; the
recovery figure is retained as an asset but replaced on the page by the
interactive field demonstration. No original media files have been deleted.

LIBERO ablation values (11.84%, 9.80%, 49.64%) match the final aggregate preserved
in the local research repository at `paper/evidence/sim_final_20260914/`.
They are pooled success rates across five evaluation replicates, not five
independently trained models. No claims of statistical significance are made.

All four tables from `Downloads/ICRA2027_DSP.pdf` (pages 5-6) were transcribed
on 2026-09-29. At the user's request, all nine displayed tables, their results
commentary and the Scope section have been removed from the homepage.
The unchanged paper remains linked for full results. The archived 55 success
entries and 12 median push distances retain their original precision.

Verify the numbers and browser rendering with:

```powershell
py scripts/check_results.py
py scripts/check_site.py
```

The first check compares archived values to the bundled paper and confirms that
the homepage has no tables. It requires PyMuPDF, Playwright, and Microsoft Edge.
Browser checks cover desktop and mobile layouts,
the eight experiment clips, per-task controls, and local links.

## Before Public Release

- Confirm author affiliations, author notes and the final paper/arXiv link.
- Replace working method figures and verify all frame captions with the recordings.
- Add approved videos and a verified BibTeX entry when available.
- Review all results against the submitted manuscript, including uncertainty reporting.
- Check anonymous-review and coauthor publication requirements.
- Confirm rights to publish every image, recording and paper.
- Confirm permission to reuse the VisualForce website source (no explicit license found).

## Privacy

The user approved public release. GitHub Pages publishes the root of `main`.
The homepage permits indexing and provides a canonical URL and `sitemap.xml`;
search engines still decide when and whether to index it.

No analytics or external scripts are loaded. Like the reference site, the page
requests Source Sans 3 from Google Fonts, with local system-font fallbacks.
