# Build with DataHub Hackathon Rules Snapshot

**Verified:** August 3, 2026
**Purpose:** Working compliance snapshot for the EvidenceGraph submission.
**Controlling source:** <https://datahub.devpost.com/rules>

This document summarizes the current published rules and the fields observed in
the live Devpost submission workflow. It is not legal advice. The Official
Rules prevail over this snapshot and over inconsistent event-page or form text.

## Official sources

- Event overview: <https://datahub.devpost.com/>
- Official Rules: <https://datahub.devpost.com/rules>
- Organizer updates: <https://datahub.devpost.com/updates>
- Devpost Terms of Service: <https://info.devpost.com/terms>

## Dates and time-zone normalization

| Event | Official Eastern Time | UTC | Asia/Shanghai |
|---|---:|---:|---:|
| Registration and submission opens | July 6, 2026, 9:00 AM EDT | July 6, 13:00 | July 6, 21:00 |
| Registration, submission, and feedback close | **August 10, 2026, 5:00 PM EDT** | **August 10, 21:00** | **August 11, 05:00** |
| Judging opens | August 17, 2026, 10:00 AM EDT | August 17, 14:00 | August 17, 22:00 |
| Judging closes | August 31, 2026, 5:00 PM EDT | August 31, 21:00 | September 1, 05:00 |
| Winners announced, approximately | September 8, 2026, 2:00 PM EDT | September 8, 18:00 | September 9, 02:00 |

The event page expressly renders the submission deadline as August 11, 2026 at
05:00 for GMT+8. EvidenceGraph's internal completion target is August 10, 2026
at 18:00 Asia/Shanghai, eleven hours before the official deadline.

## Eligibility

The event is open to eligible individuals, teams of eligible individuals, and
existing legal organizations. An individual must be at least 18 or have reached
the age of majority where they reside. A team or organization must appoint one
eligible representative to submit and act on its behalf. The Rules state no
numerical maximum team size. An eligible individual may enter individually and
may participate in more than one team or organization.

Excluded entrants include residents or organizations in jurisdictions where
United States or local law prohibits participation or prize receipt, including
the listed standard exceptions; promotion entities and specified relatives or
household members; judges and their employers; relevant affiliates; and actual
or apparent conflicts of interest.

### China eligibility caveat

China is not named among the standard excluded jurisdictions and appears as an
available country in the live submission form. An ordinary adult resident of
China is therefore eligible under the published event terms unless a specific
legal, sanctions, affiliation, or conflict restriction applies. Cash payment is
still conditional on identity, qualification, and contribution verification;
timely winner affidavits and tax forms; accurate bank information; and
compliance with applicable tax, withholding, banking, currency-conversion, and
foreign-exchange rules. The sponsor, administrator, and payment providers make
the final eligibility and payout determinations.

## Required project characteristics

The entrant must create a working software application using open-source
DataHub together with at least one of these official agent interfaces:

- DataHub MCP Server;
- Agent Context Kit;
- DataHub Skills; or
- Analytics Agent.

The application must solve one or more stated challenge problems, install and
run consistently on its intended platform, and behave as depicted in its video
and written description. Although a project may combine challenge ideas, the
live form requires one prize category:

1. Agents That Do Real Work;
2. Metadata-Aware Code Generation & Development;
3. Production ML Agents; or
4. Open / Wildcard.

## New work and prior work

The submitted project must be newly created during the July 6-August 10, 2026
submission period. Standard development tools, frameworks, libraries, starter
templates, and AI coding assistants are permitted. Other incorporated
pre-existing code or work must be disclosed. Open-source software and hardware
may be used only in compliance with their licenses, and the submission must
enhance or build upon their functionality.

EvidenceGraph must remain materially and demonstrably unique from the entrant's
prior public **MandateGuard** submission. The prior submission must not be
duplicated, relabeled, overwritten, or represented as newly created work.
EvidenceGraph should have its own repository, implementation, assets, outputs,
and project narrative. Any legitimate prior influence or reuse must be described
accurately in the pre-existing-work field.

The Official Rules permit multiple submissions only when each is unique and
substantially different, as determined by the sponsor and Devpost.

## Repository, license, demo, and video

The submission must provide:

- an easy-access project URL for judging and testing;
- a public code repository containing all necessary source code, assets, and
  complete functional setup instructions;
- an Apache License 2.0 file at the repository root, detectable and visible at
  the top of the repository page in its About area;
- an English project description covering functionality, technologies, and
  data used; and
- a public demonstration video under three minutes that shows the project
  functioning on its intended device or platform.

The Official Rules permit video hosting on YouTube, Vimeo, or Youku. Judges are
not required to watch beyond three minutes. The video may not contain third-party
trademarks, copyrighted music, or other protected material without permission.

A functioning demo, website, or test build must remain available free of charge
and without restriction through the end of judging. If a testing surface is
private, working credentials must be included in the testing instructions.
Judges may elect to judge solely from the description, images, and video, so
those materials must stand on their own. Direct links to representative sample
outputs are recommended when the project generates code, queries, reports, or
transformations.

All submission materials must be in English or include complete English
translations, including the video, description, and testing instructions.

## Live submission fields observed

The current workflow contains five sections: Manage team, Project overview,
Project details, Additional info, and Submit.

### Manage team

- Optional teammate invitations and current-team review.

### Project overview

- Required project name.
- Required elevator pitch.
- Project thumbnail; presentation field without a required marker in the
  inspected form.

### Project details

- Required About/project story in Markdown.
- Required Built with technologies, up to 25 tags.
- Try-it-out links for the demo, repository, or equivalent access.
- Optional image gallery, up to 15 images, with captions.
- Required public video-demo URL.

### Additional info

- Required single challenge category.
- Required public code-repository URL.
- Project URL providing easy test access; required by the Official Rules even
  though the inspected form label did not display a required marker.
- Optional direct sample-output URL.
- Required DataHub-technologies-used multi-select.
- Optional DataHub contribution links for the judging bonus.
- Required country or countries of residence for prize eligibility.
- Required confirmation that the project is new within the submission period.
- Conditional description of non-standard pre-existing work.
- Required feedback-prize opt-in choice. If opted in, the form requests specific
  feedback about polished features, lost time or setup friction, desired future
  engineering work, and bugs or unexpected behavior.

### Submit

- Final review reminder.
- Required agreement to the Official Rules and Devpost Terms of Service.
- Final submission action. Submitted projects may still be edited before the
  deadline, but not after it.

## Judging and prizes

Stage One is a pass/fail viability screen for theme fit and reasonable use of
the required DataHub APIs or SDKs. Stage Two applies five equally weighted core
criteria:

1. meaningful use of DataHub;
2. technical execution;
3. originality;
4. real-world usefulness; and
5. submission quality.

A meaningful open-source DataHub contribution is an optional bonus. The first
criterion expressly favors deep use of the DataHub context graph and useful
write-back over superficial metadata reads. Tie-breaking starts with the first
listed criterion.

The published cash pool is $20,500: one $6,000 Grand Prize; four $3,000
Challenge Winner prizes, one per category; two $1,000 Honourable Mentions; and
ten $50 feedback prizes. Each eligible project may win one project prize. The
individual feedback prize is separate and may be won alongside a project prize.

## Intellectual property and publicity

Entrants retain submission ownership and grant the sponsor a non-exclusive
license for judging. The sponsor and Devpost receive specified promotional
rights in the submission and contributors' names, likenesses, voices, and
images during the event and for three years afterward. Entrants warrant that
the submission is original, solely owned by the entrant or entrant group, free
of malicious code, and non-infringing. Third-party tools, data, media, and other
materials require appropriate authorization and license compliance.

## Pre-submit rule recheck

Immediately before submission:

1. Reopen the Official Rules, overview, and organizer updates and compare their
   deadline, eligibility, prize, judging, and submission language with this
   snapshot.
2. Confirm the Devpost clock displays August 11, 2026 at 05:00 for GMT+8.
3. Confirm the selected challenge category and all required live fields.
4. Verify the public repository, root Apache-2.0 license detection, clean setup,
   demo, sample outputs, and every public URL in a signed-out session.
5. Verify the video is public, functional, licensed, and strictly under three
   minutes.
6. Recheck the new-project and pre-existing-work statements for accuracy.
7. Reconfirm that EvidenceGraph is substantially different from MandateGuard
   and does not duplicate or overwrite the prior submission.
8. Confirm all public materials are professional English and contain no secret,
   private link, credential, cookie, personal data, or unsupported claim.
9. Submit before the internal target and retain a non-secret, timestamped
   confirmation that Devpost shows the project as submitted.

No organizer update visible as of the verification date changed the official
deadline, eligibility, prize structure, or judging criteria. Because the Rules
reserve amendment rights and provide no visible revision history, this snapshot
must be revalidated before final submission.
