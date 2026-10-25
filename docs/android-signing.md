# Android Beta signing maintenance

Approved by the maintainer on 25 October 2026 (Asia/Singapore): establish one durable identity and publish a reinstall-required 3.3 Beta. This is distinct from the historical debug identity.

| Identity | Public certificate SHA-256 |
| --- | --- |
| Durable Beta, RSA-4096, PKCS12, alias `lgxt-android-beta` | `0ec0084b65aff166d379206ca244ea54904511e95573b15fd2159bd4bd604114` |
| Historical 3.2.1, Android Debug DN | `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49` |

The durable certificate expires 16 October 2056 UTC. Its public pin is committed in `packaging/android/signing-identity.json` and independently configured as the `ANDROID_CERTIFICATE_SHA256` Environment variable. Never silently replace this identity; later releases must use the same private key for in-place upgrades from this Beta.

## Custody and verified recovery

The local working PKCS12 is outside Git in the maintainer's `.lgxt-release-signing/android-beta` folder. Its random, unique store/key password is protected locally using Windows user-scoped DPAPI. Files/directories restrict access to the current user and SYSTEM. No private material is in repository files or public artifacts.

A separate authenticated AES-256-GCM backup on D: contains the PKCS12, password, alias and recovery metadata. Its random 256-bit recovery key/instructions are in a separate ACL-protected `.lgxt-signing-recovery` folder on C:. Recovery was tested by decrypting the files from disk, reopening the restored PKCS12, signing/verifying a random challenge, independently exporting the restored certificate with JDK keytool, and using the restored credentials to sign an APK that Android SDK apksigner verified against the public pin. That local smoke APK is not the release artifact.

These are separate local directories/volumes, not proven independent physical media or offsite storage. Keep an encrypted backup copy offline and its recovery file in a separate protected location. Both are needed for recovery; DPAPI alone cannot recover the password on another Windows account/machine. Never commit either file or paste its contents into an issue/chat/log.

GitHub Environment `android-beta-signing` has a custom deployment-branch policy permitting only `main`, with two Secrets: `ANDROID_KEYSTORE_BASE64` and `ANDROID_KEYSTORE_PASSWORD`. Base64 is transport encoding, not encryption; GitHub stores these as encrypted Secrets. The PKCS12 uses one strong password for store/key, as required by its tooling; the alias and certificate pin are public. No repository-wide signing Secrets were added. Environment protection and Secret behavior follow [GitHub's documentation](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).

## Build and publication sequence

1. Review changes through a PR; required CI/security/CodeForge must pass and merge to `main`.
2. Dispatch `Android APK` from that exact `main` commit with `release_signing=true` and no reused candidate run. It builds the ordinary APK and isolated debug fixture separately.
3. Only the signing job receives Environment credentials. It signs after Flet build using [Android apksigner](https://developer.android.com/tools/apksigner), then deletes its temporary keystore. Passwords enter via environment references, never command-line values. The application payload must remain byte-identical across signing.
4. Fail closed on missing Secrets, wrong public pin, debug certificate/debuggable app, synthetic payload, incorrect package/version/SDK/ABI, ZIP integrity or checksum mismatch. SDK Build Tools are pinned to 36.0.0. Publish only the `lgxt-android-release-signed` artifact after the full run passes.
5. Install the exact signed APK in Android 15 x86_64 emulation, check default HTTP rejection and native note backup/import, then run the separate synthetic fixture. The signing workflow has read-only repository permissions and never publishes automatically.
6. Download the signed artifact, independently repeat SDK/signature/checksum/source checks. Only then create immutable `v3.3.0-android` at that source commit. Tag pushes intentionally do not start a different build: this order preserves the exact bytes already accepted before tagging.
7. Create a GitHub draft marked Pre-release, upload the exact seven assets, download them afresh and run `verify_release.py` with source/certificate pins. Publish only after all gates pass; download/reverify the published assets, tag and Beta state again. Never upload a fixture/test-only APK, private key, password or recovery archive.

No historical release, tag or asset may be replaced. Installation/data migration is documented in [the Android guide](android-beta.md). Actual release outcomes belong in [VERIFICATION](VERIFICATION.md).

## 3.3 publication outcome

[v3.3.0-android Beta](https://github.com/styayur/LGXT-Assistant/releases/tag/v3.3.0-android) was published from `e402b78e558cc763b0e1fad87991674bb8bc831f` after [full signed build/native acceptance](https://github.com/styayur/LGXT-Assistant/actions/runs/40167960538). Draft and published bytes were independently downloaded and verified. The import dialog/view race discovered in withheld candidates was fixed and retested in a fresh build. The certificate and verified backup remained unchanged. Exact tag rule 25790565 prohibits update/deletion. A read-only companion workflow can reverify existing signed artifacts only after proving successful main build/sign provenance, unchanged app/build inputs and matching SDK source/certificate/checksums; it cannot sign or publish. Always tag the APK identity source, not a later test-driver commit.
