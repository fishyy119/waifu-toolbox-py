/** @type {import('prettier').Config} */
export default {
  tabWidth: 2,
  printWidth: 100,
  endOfLine: 'lf',
  semi: false,
  singleQuote: true,
  trailingComma: 'all',
  tailwindStylesheet: './src/styles.css',
  plugins: ['prettier-plugin-tailwindcss'],
}
