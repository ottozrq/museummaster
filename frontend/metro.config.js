const { getDefaultConfig } = require("expo/metro-config");

/**
 * Metro configuration
 * Enable SVG files to be imported as React components.
 * This follows the recommended pattern for Expo SDK 54.
 */
module.exports = (async () => {
  /** @type {import('metro-config').MetroConfig} */
  const config = await getDefaultConfig(__dirname);
  const { transformer, resolver } = config;

  return {
    ...config,
    transformer: {
      ...transformer,
      babelTransformerPath: require.resolve("react-native-svg-transformer"),
    },
    resolver: {
      ...resolver,
      assetExts: resolver.assetExts.filter((ext) => ext !== "svg"),
      sourceExts: [...resolver.sourceExts, "svg"],
    },
  };
})();


