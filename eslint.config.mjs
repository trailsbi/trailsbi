// Lints the report page's script with the rules Microsoft applies to Power BI custom visuals,
// since the TrailsBI visual runs this same script inside Power BI.
//   npm install --no-save eslint@9 eslint-plugin-powerbi-visuals
//   npx eslint src/trailsbi/web/js
import powerbiVisuals from "eslint-plugin-powerbi-visuals";

const recommended = powerbiVisuals.configs.recommended;

export default [
    { ignores: ["node_modules/**", "dist/**", "build/**"] },
    {
        ...recommended,
        files: ["src/trailsbi/web/js/**/*.js"],
        // Each file is a piece of one classic script, not a module.
        languageOptions: { ...recommended.languageOptions, sourceType: "script" },
    },
];
