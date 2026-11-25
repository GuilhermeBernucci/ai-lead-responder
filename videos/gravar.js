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
      ["This is Fresh Cuts, a demo barbershop website with an AI booking assistant built in. Let me show you how a client books a cut.",
        async (p) => { await p.goto(URL); }],
      ["A client just types what they want, like a skin fade on Friday at 3 PM. The assistant checks your real calendar and confirms the time.",
        async (p) => { await p.click("#sugestoes button >> nth=0"); }],
      ["Then it asks for a name and phone number, and the appointment is booked. No calls and no back-and-forth texts, even at two in the morning.",
        async (p) => { await p.type("#txt", "My name is Carlos, 305-555-0199", { delay: 45 }); await p.press("#txt", "Enter"); }],
      ["The rest of the site shows your services, prices, barbers and reviews. On the annual plan, we build this website for you, for free.",
        async (p) => { await rolar(p, 2600); }],
      ["Now the owner's side. Your dashboard shows every appointment the assistant booked, grouped by day, and how much is on the calendar.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 500); }],
      ["Open any appointment to see what happens next: a reminder the day before, a heads-up two hours before, and a rebooking text four weeks later.",
        async (p) => { const s = p.locator("details summary").first(); await s.scrollIntoViewIfNeeded(); await s.click(); }],
      ["Plans start at forty-nine dollars a month. Choose annual and get two months free, plus your new website. Ready to stop missing bookings?",
        async (p) => { await p.goto(URL + "/planos"); await espera(3000); await rolar(p, 400); }],
    ],
    pt: [
      ["Esta é a Fresh Cuts, um site de barbearia de demonstração com um assistente de agendamento com inteligência artificial. Veja como o cliente marca um horário.",
        async (p) => { await p.goto(URL); }],
      ["O cliente só escreve o que quer, por exemplo, um degradê na sexta às três da tarde. O assistente confere a agenda de verdade e confirma o horário.",
        async (p) => { await p.click("#sugestoes button >> nth=0"); }],
      ["Depois ele pede nome e telefone, e pronto: o horário está marcado. Sem ligação e sem troca de mensagens, mesmo às duas da manhã.",
        async (p) => { await p.type("#txt", "My name is Carlos, 305-555-0199", { delay: 45 }); await p.press("#txt", "Enter"); }],
      ["O resto do site mostra serviços, preços, barbeiros e avaliações. No plano anual, este site é feito para o cliente de graça.",
        async (p) => { await rolar(p, 2600); }],
      ["Agora, o lado do dono. O painel mostra todos os horários que o assistente marcou, separados por dia, e quanto já tem de serviço na agenda.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 500); }],
      ["Abrindo qualquer horário, o dono vê o que vai acontecer: um lembrete na véspera, um aviso duas horas antes, e uma mensagem para remarcar quatro semanas depois.",
        async (p) => { const s = p.locator("details summary").first(); await s.scrollIntoViewIfNeeded(); await s.click(); }],
      ["Os planos são mensais. No plano anual, o cliente ganha dois meses grátis e o site profissional. É assim que a barbearia para de perder clientes.",
        async (p) => { await p.goto(URL + "/planos"); await espera(3000); await rolar(p, 400); }],
    ],
  },
  construcao: {
    en: [
      ["This is Summit Build and Remodel, a demo contractor website with an AI assistant behind the estimate form.",
        async (p) => { await p.goto(URL); }],
      ["A homeowner fills in the form: project type, budget, when they want to start, and a few details about the job.",
        async (p) => { await preencher(p); }],
      ["Within seconds, they get a personal reply by email, so they know you're on it, even at midnight.",
        async (p) => { await Promise.all([p.waitForNavigation(), p.click(".form button")]); }],
      ["On your dashboard, every lead is already sorted for you: call today, call this week, or keep in touch.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 420); }],
      ["Each lead shows the likely job size, their budget and timeline, and the questions to ask on the call. One tap and you're calling them.",
        async (p) => { const s = p.locator("details summary").first(); await s.click(); await espera(1500); await rolar(p, 300); }],
      ["On the annual plan, we also build your website for free, with the AI estimate form built in. Stop losing jobs to whoever answers first.",
        async (p) => { await p.goto(URL); await espera(1500); await rolar(p, 1800); }],
    ],
    pt: [
      ["Esta é a Summit Build and Remodel, um site de construtora de demonstração com um assistente de inteligência artificial no formulário de orçamento.",
        async (p) => { await p.goto(URL); }],
      ["O cliente preenche o formulário: tipo de obra, orçamento, quando quer começar e alguns detalhes do projeto.",
        async (p) => { await preencher(p); }],
      ["Em segundos, ele recebe uma resposta personalizada por e-mail, e sabe que a empresa já está cuidando do pedido, mesmo à meia-noite.",
        async (p) => { await Promise.all([p.waitForNavigation(), p.click(".form button")]); }],
      ["No painel, cada pedido já chega separado por prioridade: ligar hoje, ligar esta semana, ou manter contato.",
        async (p) => { await p.goto(URL + "/painel"); await espera(2500); await rolar(p, 420); }],
      ["Cada pedido mostra o tamanho provável da obra, o orçamento e o prazo do cliente, e as perguntas para fazer na ligação.",
        async (p) => { const s = p.locator("details summary").first(); await s.click(); await espera(1500); await rolar(p, 300); }],
      ["No plano anual, o site profissional sai de graça, já com o formulário inteligente. Assim a empresa para de perder obras para quem responde primeiro.",
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
  await p.type("input[name=telefone]", "(214) 555-0190", { delay: 40 });
  await p.type("input[name=email]", "robert@example.com", { delay: 30 });
  await p.selectOption("select[name=tipo]", "Roofing");
  await p.selectOption("select[name=orcamento]", "$10k - $30k");
  await p.type("textarea", "Hail damage last week: several shingles missing and a leak in the upstairs bedroom. Insurance already approved.", { delay: 25 });
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
  const navegador = await chromium.launch();
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
