module.exports = {
  testDir: __dirname,
  // La simulation apiculteur est longue : lancee seulement par
  // scripts/linux/simulation_apiculteur.sh, jamais par les gates.
  testIgnore: process.env.BEEVARIUM_SIMULATION ? [] : ["**/simulation-*.spec.js"],
  timeout: 45000,
  expect: { timeout: 10000 },
  // Sequentiel: les tests partagent la meme base et le meme serveur de test.
  workers: 1,
  reporter: [["list"]],
  use: {
    headless: true,
    actionTimeout: 10000,
    trace: "retain-on-failure",
  },
};
