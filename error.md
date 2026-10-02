Running 'gradlew :app:assembleRelease' in /home/expo/workingdir/build/ScamShield-Mobile/android
Downloading https://services.gradle.org/distributions/gradle-8.14.3-bin.zip
10%.
20%.
30%.
40%.
50%.
60%.
70%.
80%.
90%.
100%
Welcome to Gradle 8.14.3!
Here are the highlights of this release:
 - Java 24 support
 - GraalVM Native Image toolchain selection
- Enhancements to test reporting
 - Build Authoring improvements
For more details see https://docs.gradle.org/8.14.3/release-notes.html
To honour the JVM settings for this build a single-use Daemon process will be forked. For more on this, please refer to https://docs.gradle.org/8.14.3/userguide/gradle_daemon.html#sec:disabling_the_daemon in the Gradle documentation.
Daemon will be stopped at the end of the build
> Configure project :expo-gradle-plugin:expo-autolinking-plugin
w: file:///home/expo/workingdir/build/ScamShield-Mobile/node_modules/expo-modules-autolinking/android/expo-gradle-plugin/expo-autolinking-plugin/build.gradle.kts:25:3: 'kotlinOptions(KotlinJvmOptionsDeprecated /* = KotlinJvmOptions */.() -> Unit): Unit' is deprecated. Please migrate to the compilerOptions DSL. More details are here: https://kotl.in/u1r8ln
> Configure project :expo-gradle-plugin:expo-autolinking-settings-plugin
w: file:///home/expo/workingdir/build/ScamShield-Mobile/node_modules/expo-modules-autolinking/android/expo-gradle-plugin/expo-autolinking-settings-plugin/build.gradle.kts:30:3: 'kotlinOptions(KotlinJvmOptionsDeprecated /* = KotlinJvmOptions */.() -> Unit): Unit' is deprecated. Please migrate to the compilerOptions DSL. More details are here: https://kotl.in/u1r8ln
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :gradle-plugin:shared:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :gradle-plugin:settings-plugin:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:pluginDescriptors
> Task :gradle-plugin:settings-plugin:pluginDescriptors
> Task :gradle-plugin:settings-plugin:processResources
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:processResources
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:processResources NO-SOURCE
> Task :gradle-plugin:shared:processResources NO-SOURCE
> Task :gradle-plugin:shared:compileKotlin
> Task :gradle-plugin:shared:compileJava NO-SOURCE
> Task :gradle-plugin:shared:classes UP-TO-DATE
> Task :gradle-plugin:shared:jar
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:compileKotlin
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:compileJava NO-SOURCE
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:classes UP-TO-DATE
> Task :expo-gradle-plugin:expo-autolinking-plugin-shared:jar
> Task :gradle-plugin:settings-plugin:compileKotlin
> Task :gradle-plugin:settings-plugin:compileJava NO-SOURCE
> Task :gradle-plugin:settings-plugin:classes
> Task :gradle-plugin:settings-plugin:jar
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:compileKotlin
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:compileJava NO-SOURCE
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:classes
> Task :expo-gradle-plugin:expo-autolinking-settings-plugin:jar
> Configure project :expo-module-gradle-plugin
w: file:///home/expo/workingdir/build/ScamShield-Mobile/node_modules/expo-modules-core/expo-module-gradle-plugin/build.gradle.kts:58:3: 'kotlinOptions(KotlinJvmOptionsDeprecated /* = KotlinJvmOptions */.() -> Unit): Unit' is deprecated. Please migrate to the compilerOptions DSL. More details are here: https://kotl.in/u1r8ln
> Task :expo-gradle-plugin:expo-autolinking-plugin:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :expo-module-gradle-plugin:checkKotlinGradlePluginConfigurationErrors
SKIPPED
> Task :gradle-plugin:react-native-gradle-plugin:checkKotlinGradlePluginConfigurationErrors SKIPPED
> Task :expo-module-gradle-plugin:pluginDescriptors
> Task :expo-module-gradle-plugin:processResources
> Task :expo-gradle-plugin:expo-autolinking-plugin:pluginDescriptors
> Task :expo-gradle-plugin:expo-autolinking-plugin:processResources
> Task :gradle-plugin:react-native-gradle-plugin:pluginDescriptors
> Task :gradle-plugin:react-native-gradle-plugin:processResources
> Task :expo-gradle-plugin:expo-autolinking-plugin:compileKotlin
> Task :expo-gradle-plugin:expo-autolinking-plugin:compileJava NO-SOURCE
> Task :expo-gradle-plugin:expo-autolinking-plugin:classes
> Task :expo-gradle-plugin:expo-autolinking-plugin:jar
> Task :gradle-plugin:react-native-gradle-plugin:compileKotlin
> Task :gradle-plugin:react-native-gradle-plugin:compileJava NO-SOURCE
> Task :gradle-plugin:react-native-gradle-plugin:classes
> Task :gradle-plugin:react-native-gradle-plugin:jar
> Task :expo-module-gradle-plugin:compileKotlin
w: file:///home/expo/workingdir/build/ScamShield-Mobile/node_modules/expo-modules-core/expo-module-gradle-plugin/src/main/kotlin/expo/modules/plugin/android/AndroidLibraryExtension.kt:9:24 'var targetSdk: Int?' is deprecated. Will be removed from library DSL in v9.0. Use testOptions.targetSdk or/and lint.targetSdk instead.
> Task :expo-module-gradle-plugin:compileJava NO-SOURCE
> Task :expo-module-gradle-plugin:classes
> Task :expo-module-gradle-plugin:jar
> Configure project :
[32m[ExpoRootProject][0m Using the following versions:
  - buildTools:  [32m36.0.0[0m
  - minSdk:      [32m24[0m
  - compileSdk:  [32m36[0m
  - targetSdk:   [32m36[0m
  - ndk:         [32m27.1.12297006[0m
  - kotlin:      [32m2.1.20[0m
  - ksp:         [32m2.1.20-2.0.1[0m
> Configure project :expo
Using expo modules
- [32mexpo-constants[0m (18.0.13)
  - [32mexpo-modules-core[0m (3.0.30)
  - [33m[📦][0m [32mexpo-application[0m (7.0.8)
  - [33m[📦][0m [32mexpo-asset[0m (12.0.13)
  - [33m[📦][0m [32mexpo-background-fetch[0m (14.0.9)
  - [33m[📦][0m [32mexpo-file-system[0m (19.0.22)
  - [33m[📦][0m [32mexpo-font[0m (14.0.11)
  - [33m[📦][0m [32mexpo-keep-awake[0m (15.0.8)
  - [33m[📦][0m [32mexpo-linking[0m (8.0.12)
  - [33m[📦][0m [32mexpo-notifications[0m (0.32.17)
  - [33m[📦][0m [32mexpo-task-manager[0m (14.0.9)
  - [33m[📦][0m [32munimodules-app-loader[0m (6.0.8)
Checking the license for package Android SDK Build-Tools 36 in /home/expo/Android/Sdk/licenses
License for package Android SDK Build-Tools 36 accepted.
Preparing "Install Android SDK Build-Tools 36 v.36.0.0".
"Install Android SDK Build-Tools 36 v.36.0.0" ready.
Installing Android SDK Build-Tools 36 in /home/expo/Android/Sdk/build-tools/36.0.0
"Install Android SDK Build-Tools 36 v.36.0.0" complete.
"Install Android SDK Build-Tools 36 v.36.0.0" finished.
[=========                              ] 25%                                   
[=========                              ] 25% Fetch remote repository...        
[=======================================] 100% Fetch remote repository...
> Task :expo-modules-core:preBuild UP-TO-DATE
> Task :react-native-async-storage_async-storage:preBuild UP-TO-DATE
> Task :react-native-get-sms-android:preBuild UP-TO-DATE
> Task :app:generateAutolinkingPackageList
> Task :app:generateCodegenSchemaFromJavaScript SKIPPED
> Task :app:generateCodegenArtifactsFromSchema SKIPPED
> Task :app:generateReactNativeEntryPoint
> Task :react-native-reanimated:assertMinimalReactNativeVersionTask
> Task :react-native-safe-area-context:preBuild UP-TO-DATE
> Task :react-native-screens:preBuild UP-TO-DATE
> Task :react-native-reanimated:assertNewArchitectureEnabledTask FAILED
> Task :react-native-worklets:assertMinimalReactNativeVersionTask
> Task :expo-constants:createExpoConfig
The NODE_ENV environment variable is required but was not specified. Ensure the project is bundled with Expo CLI or NODE_ENV is set. Using only .env.local and .env
> Task :expo:generatePackagesList
[Incubating] Problems report is available at: file:///home/expo/workingdir/build/ScamShield-Mobile/android/build/reports/problems/problems-report.html
FAILURE: Build failed with an exception.
* Where:
Build file '/home/expo/workingdir/build/ScamShield-Mobile/node_modules/react-native-reanimated/android/build.gradle' line: 298
* What went wrong:
Execution failed for task ':react-native-reanimated:assertNewArchitectureEnabledTask'.
> [Reanimated] Reanimated requires new architecture to be enabled. Please enable it by setting `newArchEnabled` to `true` in `gradle.properties`.
* Try:
> Run with --stacktrace option to get the stack trace.
> Run with --info or --debug option to get more log output.
> Run with --scan to get full insights.
> Get more help at https://help.gradle.org.
BUILD FAILED in 1m 59s
Deprecated Gradle features were used in this build, making it incompatible with Gradle 9.0.
You can use '--warning-mode all' to show the individual deprecation warnings and determine if they come from your own scripts or plugins.
For more on this, please refer to https://docs.gradle.org/8.14.3/userguide/command_line_interface.html#sec:command_line_warnings in the Gradle documentation.
31 actionable tasks: 31 executed
See the profiling report at: file:///home/expo/workingdir/build/ScamShield-Mobile/android/build/reports/profile/profile-2026-05-31-11-55-35.html
A fine-grained performance profile is available: use the --scan option.
Error: Gradle build failed with unknown error. See logs for the "Run gradlew" phase for more information.
