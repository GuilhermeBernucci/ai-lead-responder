// Grava um vídeo tutorial narrado de uma das demos.
// Uso: node gravar.js <barbearia|construcao> <en|pt> <pasta_saida>
// Precisa: o servidor da demo rodando em http://localhost:8000, ffmpeg, e tts.py (voz).

const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const [produto, idioma, saida] = process.argv.slice(2);
const TTS = process.env.TTS_SCRIPT;
// Troque a voz sem mexer no código: VOZ_PT=pt-BR-ThalitaMultilingualNeural, VOZ_EN=en-US-AvaMultilingualNeural
const VOZ = idioma === "pt" ? (process.env.VOZ_PT || "pt-BR-AntonioNeural") : (process.env.VOZ_EN || "en-US-AndrewNeural");
const PYTHON = process.env.PYTHON || "python3";
const URL = "http://localhost:8000";
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------- Roteiros: [fala, ação na tela] ----------
const roteiros = {
  barbearia: {
    en: [
      ["Hey! Let me show you something. This is a barbershop website with an assistant that books appointments on its own, day or night.",
        async (p) => { await p.goto(URL); }],
      ["Watch this. A client types what they want, like a skin fade Friday at three. The assistant checks the real calendar and offers that time.",
        async (p) => { await p.click("#sugestoes button >> nth=0"); }],
      ["Then it asks for a name and a phone number, and that's it, they're booked. Nobody had to pick up the phone, even at two in the morning.",
        async (p) => { await p.type("#txt", "My name is Carlos, 305-555-0199", { delay: 45 }); await p.press("#txt", "Enter"); }],
      ["The rest of the site shows your services, your prices, your barbers and your reviews. And on the annual plan, I build this website for you, for free.",
        async (p) => { await rolar(p, 2600); }],
      ["Now, here's your side. Every appointment the assistant booked shows up right here, by day, with how much money is already on the calendar.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 500); }],
      ["Open any appointment and you'll see the texts that go out on their own: a reminder the day before, a heads-up two hours before, and a nudge to rebook four weeks later.",
        async (p) => { const s = p.locator("details summary").first(); await s.scrollIntoViewIfNeeded(); await s.click(); }],
      ["Plans start at forty-nine dollars a month, and the annual plan gets you two months free plus the website. Want to stop losing bookings? Let's talk.",
        async (p) => { await p.goto(URL + "/planos"); await espera(3000); await rolar(p, 400); }],
    ],
    pt: [
      ["Oi! Deixa eu te mostrar uma coisa. Esse é um site de barbearia com um assistente que marca horário sozinho, de dia ou de madrugada.",
        async (p) => { await p.goto(URL); }],
      ["Olha só. O cliente escreve o que quer, tipo um degradê na sexta às três. O assistente confere a agenda de verdade e oferece o horário.",
        async (p) => { await p.click("#sugestoes button >> nth=0"); }],
      ["Aí ele pede o nome e o telefone, e pronto, tá marcado. Ninguém precisou atender o telefone, nem às duas da manhã.",
        async (p) => { await p.type("#txt", "My name is Carlos, 305-555-0199", { delay: 45 }); await p.press("#txt", "Enter"); }],
      ["O resto do site mostra os serviços, os preços, os barbeiros e as avaliações. E no plano anual, eu faço esse site pra você, de graça.",
        async (p) => { await rolar(p, 2600); }],
      ["Agora, o seu lado. Tudo o que o assistente marcou aparece aqui, separado por dia, com quanto já tem de serviço na agenda.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 500); }],
      ["Abrindo qualquer horário, você vê as mensagens que saem sozinhas: um lembrete na véspera, um aviso duas horas antes, e um convite pra voltar quatro semanas depois.",
        async (p) => { const s = p.locator("details summary").first(); await s.scrollIntoViewIfNeeded(); await s.click(); }],
      ["Os planos são mensais, e no anual você ganha dois meses grátis e ainda leva o site. Quer parar de perder cliente? Bora conversar.",
        async (p) => { await p.goto(URL + "/planos"); await espera(3000); await rolar(p, 400); }],
    ],
  },
  construcao: {
    en: [
      ["Let me show you something. This is a contractor website, and behind the estimate form there's an AI assistant working for you.",
        async (p) => { await p.goto(URL); }],
      ["A homeowner fills in the form: what kind of project, the budget, when they want to start, and a few details about the job.",
        async (p) => { await preencher(p); }],
      ["Seconds later, they get a personal email back. So they know you're on it, even if they wrote to you at midnight.",
        async (p) => { await Promise.all([p.waitForNavigation(), p.click(".form button")]); }],
      ["On your dashboard, every lead is already sorted for you: call today, call this week, or just keep in touch.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 420); }],
      ["Each lead shows the likely job size, their budget and timeline, and the questions to ask on the call. One tap, and you're calling them.",
        async (p) => { const s = p.locator("details summary").first(); await s.click(); await espera(1500); await rolar(p, 300); }],
      ["And on the annual plan, I build your website for free, with this form already in it. Stop losing jobs to whoever answers first.",
        async (p) => { await p.goto(URL); await espera(1500); await rolar(p, 1800); }],
    ],
    pt: [
      ["Deixa eu te mostrar uma coisa. Esse é um site de construtora, e por trás do formulário de orçamento tem um assistente de inteligência artificial trabalhando pra você.",
        async (p) => { await p.goto(URL); }],
      ["O cliente preenche o formulário: o tipo de obra, o orçamento, quando quer começar e alguns detalhes do serviço.",
        async (p) => { await preencher(p); }],
      ["Segundos depois, ele recebe um e-mail personalizado. Assim ele já sabe que você está cuidando do pedido, mesmo que tenha escrito à meia-noite.",
        async (p) => { await Promise.all([p.waitForNavigation(), p.click(".form button")]); }],
      ["No seu painel, cada pedido já chega separado: ligar hoje, ligar esta semana, ou só manter contato.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 420); }],
      ["Cada pedido mostra o tamanho provável da obra, o orçamento e o prazo do cliente, e as perguntas pra fazer na ligação. Um toque e você já está ligando.",
        async (p) => { const s = p.locator("details summary").first(); await s.click(); await espera(1500); await rolar(p, 300); }],
      ["E no plano anual, eu faço o seu site de graça, já com esse formulário. Chega de perder obra pra quem responde primeiro.",
        async (p) => { await p.goto(URL); await espera(1500); await rolar(p, 1800); }],
    ],
  },
};

async function rolar(p, total) {
  for (let i = 0; i < total; i += 20) { await p.mouse.wheel(0, 20); await espera(16); }
}

async function preencher(p) {
  await p.locator(".form").scrollIntoViewIfNeeded();
  await p.type("input[name=nome]", "Robert Hayes", { delay: 40 });
  await p.type("input[name=telefone]", idioma === "pt" ? "(11) 98765-4321" : "(214) 555-0190", { delay: 40 });
  await p.type("input[name=email]", "robert@example.com", { delay: 30 });
  await p.selectOption("select[name=tipo]", "Roofing");
  await p.selectOption("select[name=orcamento]", "$10k - $30k");
  const detalhes = idioma === "pt"
    ? "Granizo na semana passada: faltam várias telhas e tem uma goteira no quarto de cima. O seguro já aprovou."
    : "Hail damage last week: several shingles missing and a leak in the upstairs bedroom. Insurance already approved.";
  await p.type("textarea", detalhes, { delay: 25 });
}

// Legenda fixa na parte de baixo da tela (sobrevive às trocas de página)
async function legenda(p, texto) {
  await p.evaluate((t) => {
    let el = document.getElementById("__legenda");
    if (!el) {
      el = document.createElement("div");
      el.id = "__legenda";
      el.style.cssText = "position:fixed;left:32px;bottom:24px;width:660px;" +
        "background:rgba(10,10,10,.85);color:#fff;font:500 20px/1.45 system-ui,sans-serif;padding:14px 20px;border-radius:12px;" +
        "text-align:left;z-index:99999;pointer-events:none;box-shadow:0 8px 30px rgba(0,0,0,.35)";
      document.body.appendChild(el);
    }
    el.textContent = t;
  }, texto);
}

function duracao(arquivo) {
  return parseFloat(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arquivo]).toString());
}

(async () => {
  const cenas = roteiros[produto][idioma];
  const tmp = fs.mkdtempSync(path.join(saida, "tmp-"));

  // 1) Gera a narração de cada cena
  const audios = cenas.map(([fala], i) => {
    const arq = path.join(tmp, `cena${i}.mp3`);
    execFileSync(PYTHON, [TTS, VOZ, fala, arq]);
    return { arq, seg: duracao(arq) };
  });

  // 2) Grava a tela seguindo o roteiro
  // CANAL=msedge ou chrome usa o navegador já instalado, sem baixar o Chromium do Playwright
  const navegador = await chromium.launch(process.env.CANAL ? { channel: process.env.CANAL } : {});
  const contexto = await navegador.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: tmp, size: { width: 1280, height: 720 } } });
  const p = await contexto.newPage();
  const t0 = Date.now();
  p.on("load", async () => { const atual = p.__legenda; if (atual) await legenda(p, atual).catch(() => {}); });

  const inicios = [];
  for (let i = 0; i < cenas.length; i++) {
    const [fala, acao] = cenas[i];
    if (i === 0) await acao(p);
    inicios.push(Date.now() - t0);
    p.__legenda = fala;
    await legenda(p, fala).catch(() => {});
    const tempo = espera(audios[i].seg * 1000 + 700);
    if (i > 0) { await acao(p); await legenda(p, fala).catch(() => {}); }
    await tempo;
  }
  await espera(800);
  const video = await p.video().path();
  await contexto.close();
  await navegador.close();

  // 3) Junta vídeo + narração num MP4
  const entradas = ["-y", "-i", video];
  audios.forEach((a) => entradas.push("-i", a.arq));
  const atrasos = audios.map((_, i) => `[${i + 1}]adelay=${inicios[i]}|${inicios[i]}[a${i}]`).join(";");
  const mix = audios.map((_, i) => `[a${i}]`).join("") + `amix=inputs=${audios.length}:normalize=0[aud]`;
  const final = path.join(saida, `${produto}-${idioma}.mp4`);
  execFileSync("ffmpeg", [...entradas, "-filter_complex", `${atrasos};${mix}`, "-map", "0:v", "-map", "[aud]",
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", final],
    { stdio: "ignore" });
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log("ok", final, Math.round(duracao(final)) + "s");
})();
