# Ecoa

Aplicativo **portátil para Windows**, feito em Python, que toca mensagens de áudio **em loop** ou **de tempos em tempos** (minutos ou horas), apenas dentro de **faixas de horário** que você define (por exemplo, 09:00 às 18:00). Pode iniciar junto com o Windows e fica na bandeja do sistema.

> O projeto é distribuído como código-fonte e como executável portátil para Windows. A compilação e a publicação das versões são automatizadas pelo GitHub Actions. Não há instalador: basta baixar o executável na seção **Releases**.

## Recursos

- **Vários lembretes**, cada um com seu próprio áudio, volume, horário e dias da semana.
- **Dois modos**
  - **Intervalo**: toca a cada N minutos ou horas, com repetições opcionais a cada disparo.
  - **Loop contínuo**: repete o áudio sem parar durante toda a faixa de horário.
- **Faixa de horário** com início e fim, inclusive atravessando a meia-noite (22:00 às 06:00) ou o dia todo (24 h).
- **Dias da semana** configuráveis por lembrete.
- **Inicia com o Windows** (sem administrador) e **começa escondido na bandeja**.
- **Portátil**: configurações, áudios e log ficam na pasta `dados`, ao lado do programa.
- **Instância única**: abrir o app de novo só traz a janela que já está aberta.
- Interface moderna (CustomTkinter) com tema claro, escuro ou automático.
- Formatos de áudio: **MP3, WAV, OGG e FLAC**.

## Como as regras funcionam

| Conceito | Comportamento |
|---|---|
| Faixa de horário | Vale do início (inclusive) até o fim (exclusive). `09:00 às 18:00` está ativa às 17:59 e inativa às 18:00. |
| Atravessar a meia-noite | Se o fim for menor que o início (`22:00 às 06:00`), a faixa começa num dia e termina no seguinte. Os dias da semana valem para o dia em que a faixa **começa**. |
| Dia todo | Ative “Dia todo (24 h)”: o lembrete fica ativo o tempo inteiro. |
| Intervalo | Os disparos seguem uma grade **a partir do início da faixa**. Com `09:00 às 18:00` a cada 45 min: 09:00, 09:45, 10:30, 11:15... O último disparo é sempre antes do fim da faixa. |
| Loop contínuo | Começa ao entrar na faixa e para sozinho ao sair dela. A “pausa entre repetições” define o silêncio entre uma repetição e a próxima. |
| Disparo atrasado | Se o PC estava suspenso e o disparo atrasou mais de 90 s, ele é pulado (não toca “de uma vez” tudo que ficou para trás). |

Exemplos:

| Quero | Configuração |
|---|---|
| Lembrar de beber água de hora em hora no expediente | Intervalo, 1 hora, 09:00 às 18:00, Seg a Sex |
| Música de fundo durante o expediente | Loop contínuo, 09:00 às 18:00 |
| Aviso a cada 20 min, o dia todo | Intervalo, 20 minutos, Dia todo |
| Aviso de turno da noite | Intervalo, 2 horas, 22:00 às 06:00 |

## Baixar a versão pronta

1. Abra a seção [Releases](https://github.com/pablopcdossantos2-sys/ecoa-portable/releases) deste repositório.
2. Na versão desejada, baixe o arquivo `Ecoa.exe`.
3. Execute-o no Windows 10 ou 11. Na primeira execução, o Ecoa cria a pasta `dados` ao lado do executável (ou em `%APPDATA%\Ecoa\dados`, se a pasta não permitir gravação).

O executável é compilado para Windows x64 e não exige que o Python esteja instalado. Como o programa não é assinado digitalmente, o Windows SmartScreen pode exibir um aviso na primeira execução.

## Requisitos

- Windows 10 ou 11
- Python **3.10 a 3.13** (somente para rodar pelo código ou compilar; o `.exe` gerado não precisa de Python)

## Rodando pelo código (desenvolvimento)

Pelo script, que cria o ambiente virtual e instala as dependências:

```bat
run.bat
```

Ou manualmente:

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Para iniciar escondido na bandeja, como o Windows faz na inicialização: `python main.py --minimized`.

## Compilando para um programa portátil (.exe)

A compilação usa o [PyInstaller](https://pyinstaller.org).

### Opção 1: pelo script (recomendado)

1. Instale o Python 3.10+ em <https://www.python.org/downloads/> e marque **Add python.exe to PATH**.
2. Dê dois cliques em `build.bat` (ou rode no Prompt de Comando, dentro da pasta do projeto).
3. Aguarde. O script cria o ambiente virtual, instala as dependências, gera o ícone e compila.
4. O resultado fica em `dist\Ecoa.exe`.

Para gerar uma **pasta** em vez de um arquivo único (abre mais rápido):

```bat
build.bat onedir
```

O resultado fica em `dist\Ecoa\Ecoa.exe`. Leve a pasta `Ecoa` inteira.

### Opção 2: manualmente

```bat
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-build.txt
python tools\make_icon.py
pyinstaller --noconfirm --clean --windowed --onefile --name Ecoa --icon assets\icon.ico ^
  --collect-all customtkinter --hidden-import pystray._win32 main.py
```

Troque `--onefile` por `--onedir` para gerar uma pasta.

### Arquivo único ou pasta?

| | `--onefile` | `--onedir` |
|---|---|---|
| Distribuição | Um único `Ecoa.exe` | Pasta com `Ecoa.exe` e bibliotecas |
| Abertura | Mais lenta (descompacta em pasta temporária a cada início) | Mais rápida |
| Antivírus | Mais propenso a falso positivo | Menos propenso |

Como o app abre junto com o Windows, `onedir` costuma ser a escolha mais tranquila. Os dois funcionam do mesmo jeito.

### Avisos do Windows

Como o executável não é assinado digitalmente, o SmartScreen pode exibir “O Windows protegeu seu computador”. Clique em **Mais informações** e depois em **Executar assim mesmo**. Se o antivírus bloquear, gere com `build.bat onedir` ou adicione uma exclusão para a pasta do app.

## Usando a versão portátil

Copie o `Ecoa.exe` (ou a pasta `Ecoa`) para onde quiser, inclusive um pendrive. Na primeira execução ele cria, ao lado do programa:

```
Ecoa.exe
dados/
├─ config.json     lembretes e configurações
├─ audios/         cópia dos áudios usados
└─ ecoa.log        registro de eventos e erros
```

Para levar tudo para outro PC, copie o programa **junto com a pasta `dados`**. Os áudios são referenciados por caminho relativo, então nada quebra ao mudar de lugar.

Se a pasta do programa não permitir gravação (por exemplo, `C:\Program Files`), o Ecoa usa `%APPDATA%\Ecoa\dados`.

## Iniciar com o Windows

Em **Configurações → Iniciar com o Windows**. O app grava uma entrada em `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` (não precisa de administrador) que executa `Ecoa.exe --minimized`.

- Para desligar, use a mesma opção ou o **Gerenciador de Tarefas → Inicializar**.
- Se você mover o programa de pasta, basta abri-lo uma vez: ele atualiza o caminho gravado.
- Com **Começar na bandeja** ligado, o app abre escondido; clique no ícone perto do relógio para ver a janela. Se não aparecer, procure na seta de ícones ocultos da barra de tarefas.

## Bandeja do sistema

- Clique no ícone: abre a janela.
- Clique com o botão direito: **Abrir**, **Pausar lembretes** e **Sair**.
- Com **Fechar na bandeja** ligado, o botão X apenas esconde a janela e os lembretes continuam. Para encerrar de vez, use **Sair**.

## Estrutura do projeto

```
ecoa-portable/
├─ main.py                ponto de entrada
├─ build.bat / run.bat    compilar e rodar
├─ requirements.txt       dependências do app
├─ requirements-build.txt PyInstaller
├─ assets/icon.ico        ícone do executável
├─ tools/make_icon.py     gera o ícone
├─ tests/                 testes da lógica (unittest)
└─ ecoa/
   ├─ schedule.py         regras de faixa de horário e intervalo (lógica pura)
   ├─ engine.py           agendador: decide o que toca e o que para
   ├─ player.py           reprodução de áudio (pygame.mixer)
   ├─ models.py           lembretes, configurações e persistência em JSON
   ├─ autostart.py        iniciar com o Windows (registro)
   ├─ singleton.py        instância única
   ├─ tray.py / icon.py   bandeja e ícone desenhado por código
   └─ ui/                 interface (CustomTkinter)
```

## Testes

A lógica de horários, o motor e a persistência têm testes que rodam em qualquer sistema, sem interface nem áudio:

```bat
python -m unittest discover -s tests -v
```

## Solução de problemas

| Problema | O que fazer |
|---|---|
| Sem som | Confira o volume do Windows e do lembrete, use **Testar** no card e, se trocou de fone ou caixa de som, vá em **Configurações → Reiniciar áudio**. |
| O primeiro som após ligar o PC falhou | O Windows pode demorar a liberar o áudio. O app tenta reiniciar o mixer sozinho; loops tentam de novo a cada poucos segundos. |
| “Arquivo de áudio não encontrado” | O arquivo foi movido ou apagado. Edite o lembrete e escolha o áudio de novo. |
| MP3 não toca | Teste outro arquivo ou converta para WAV/OGG. Veja detalhes em `dados\ecoa.log`. |
| Não inicia com o Windows | Em **Gerenciador de Tarefas → Inicializar**, confira se “Ecoa” está **Habilitado**. |
| Erro na compilação | Use Python 3.10 a 3.13 e rode `build.bat` de novo para reinstalar as dependências. |

O arquivo `dados\ecoa.log` registra disparos, loops e erros, e ajuda a entender qualquer comportamento inesperado.

## Compilação e publicação pelo GitHub

O workflow `.github/workflows/build-release.yml` automatiza o processo no GitHub Actions, usando um runner Windows. A cada push para `main`, ele instala as dependências, executa os testes e compila `dist\Ecoa.exe`. O executável também fica disponível como artefato da execução.

A primeira publicação é criada automaticamente a partir da versão definida em `ecoa/__init__.py`. Para publicar uma versão posterior: atualize `__version__` (por exemplo, para `1.1.0`) e envie a alteração para `main`; se a tag `v1.1.0` ainda não existir, o workflow cria a Release correspondente. Também é possível publicar diretamente enviando uma tag `vX.Y.Z` ou executando o workflow manualmente com a opção **Publish release** ativada.

O `.gitignore` exclui `dados/` (configurações, áudios e logs pessoais), `dist/`, `build/` e ambientes virtuais. O executável não deve ser versionado junto ao código: ele é anexado à respectiva Release.

## Ideias para o futuro

- Escolher o dispositivo de saída de áudio.
- Lembretes com texto falando (voz sintetizada do Windows).
- Silenciar por um tempo (por exemplo, 1 hora) pela bandeja.
- Importar e exportar lembretes.
