const { ESLint } = require("eslint");

async function lintCode(code) {
  const eslint = new ESLint();

  try {
    const results = await eslint.lintText(code);
    console.log(JSON.stringify(results));
  } catch (error) {
    console.error(JSON.stringify({ error: error.message }));
  }
}

// Get the code from command line argument
const code = process.argv[2];

lintCode(code).catch(error => {
  console.error(JSON.stringify({ error: "Unexpected error in lintCode function" }));
});