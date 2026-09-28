Running "expo doctor"
Running 18 checks on your project...
15/18 checks passed. 3 checks failed. Possible issues detected:
Use the --verbose flag to see more details about passed checks.
✖ Check for common project setup issues
The .expo directory is not ignored by Git. It contains machine-specific device history and development server settings and should not be committed.
Advice:
Add ".expo/" to your .gitignore to avoid committing local Expo state.
✖ Check for issues with Metro config
It looks like that you are using a custom metro.config.js that does not extend "expo/metro-config". This can lead to unexpected and hard to debug issues. Learn more: https://docs.expo.dev/guides/customizing-metro/
Advice:
Update your "metro.config.js" to extend "expo/metro-config".
✖ Check that required peer dependencies are installed
Missing peer dependency: react-native-worklets
Required by: react-native-reanimated
Advice:
Install missing required peer dependency with "npx expo install react-native-worklets"
Your app may crash outside of Expo Go without this dependency. Native module peer dependencies must be installed directly.
3 checks failed, indicating possible issues with the project.

Command "expo doctor" failed.
npx -y expo-doctor exited with non-zero code: 1
