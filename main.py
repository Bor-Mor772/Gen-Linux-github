import subprocess, json, sys, os, shutil, time, tempfile, urllib.request, ctypes
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

if os.name == "nt":
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    os.environ["PYTHONIOENCODING"] = "utf-8"
    os.system("cls")
else:
    os.system("clear")

RED, GREEN, YELLOW, CYAN, RESET = "\033[91m", "\033[92m", "\033[93m", "\033[96m", "\033[0m"

BANNER = RED + r"""
 ██▒   █▓ ██▓███    ██████     █████▒▒█████   ██▀███  ▓██   ██▓ ▒█████   █    ██
▓██░   █▒▓██░  ██ ▒██    ▒    ▓██   ▒▒██▒  ██▒▓██ ▒ ██▒ ▒██  ██▒▒██▒  ██▒ ██  ▓██▒
 ▓██  █▒░▓██░ ██▓▒░ ▓██▄      ▒████ ░▒██░  ██▒▓██ ░▄█ ▒  ▒██ ██░▒██░  ██▒▓██  ▒██░
  ▒██ █░░▒██▄█▓▒ ▒  ▒   ██▒   ░▓█▒  ░▒██   ██░▒██▀▀█▄    ░ ▐██▓░▒██   ██░▓▓█  ░██░
   ▒▀█░  ▒██▒ ░  ░▒██████▒▒   ░▒█░   ░ ████▓▒░░██▓ ▒██▒  ░ ██▒▓░░ ████▓▒░▒▒█████▓
   ░ ▐░  ▒▓▒░ ░  ░▒ ▒▓▒ ▒ ░    ▒ ░   ░ ▒░▒░▒░ ░ ▒▓ ░▒▓░   ██▒▒▒ ░ ▒░▒░▒░  ▒▓▒ ▒ ▒
   ░ ░░  ░▒ ░     ░ ░▒  ░       ░       ░ ▒ ▒░   ░▒ ░ ▒░ ▓██ ░▒░   ░ ▒ ▒░  ░▒░ ░ ░
     ░░  ░░       ░  ░  ░       ░ ░   ░ ░ ░ ▒     ░   ░  ▒ ▒ ░░  ░ ░ ░ ▒    ░░ ░ ░
      ░                 ░     ░           ░ ░     ░      ░ ░         ░ ░     ░
""" + RESET

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".vps_foryou.json")
DEFAULT_REPO_NAME = "vps-foryou"

KNOWN_PATHS = [
    r"C:\Program Files\GitHub CLI\gh.exe",
    r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    os.path.expanduser(r"~\AppData\Local\GitHubCLI\gh.exe"),
    os.path.expanduser(r"~\AppData\Local\Programs\GitHub CLI\gh.exe"),
    os.path.expanduser(r"~\scoop\apps\gh\current\bin\gh.exe"),
    r"C:\ProgramData\chocolatey\bin\gh.exe",
]


def ts():
    return "[" + datetime.now().strftime("%H:%M:%S") + "]"


def log(msg, color=RESET):
    try:
        print(color + ts() + " " + msg + RESET, flush=True)
    except UnicodeEncodeError:
        print(ts() + " " + msg, flush=True)


def input_line(prompt):
    return input(CYAN + prompt + RESET).strip()


def run_cmd(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", "not found"
    except Exception as e:
        return 1, "", str(e)


def refresh_path():
    try:
        import winreg
        paths = []
        for root, sub in [
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            (winreg.HKEY_CURRENT_USER, r"Environment"),
        ]:
            try:
                with winreg.OpenKey(root, sub) as k:
                    v, _ = winreg.QueryValueEx(k, "Path")
                    paths.append(v)
            except OSError:
                pass
        if paths:
            os.environ["PATH"] = ";".join(paths) + ";" + os.environ.get("PATH", "")
    except Exception:
        pass


def find_gh():
    gh = shutil.which("gh")
    if gh and os.path.isfile(gh):
        return gh
    for p in KNOWN_PATHS:
        if os.path.isfile(p):
            return p
    for base in [r"C:\Program Files", r"C:\Program Files (x86)"]:
        if os.path.isdir(base):
            try:
                for entry in os.listdir(base):
                    if "github" in entry.lower() or "gh cli" in entry.lower():
                        for sub in ["gh.exe", os.path.join("bin", "gh.exe")]:
                            t = os.path.join(base, entry, sub)
                            if os.path.isfile(t):
                                return t
            except OSError:
                pass
    return None


def wait_gh_file(timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        for p in KNOWN_PATHS:
            if os.path.isfile(p):
                return p
        time.sleep(3)
    return None


def install_msi(msi_path):
    log("Requesting admin rights to install MSI...", YELLOW)
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "msiexec.exe",
            '/i "' + msi_path + '" /qb /norestart', None, 1)
        if ret <= 32:
            return False
        log("UAC accepted.", CYAN)
        return True
    except Exception:
        return False


def install_gh():
    log("gh CLI not found. Installing...", YELLOW)
    code, _, _ = run_cmd(["winget", "--version"])
    if code == 0:
        try:
            subprocess.run([
                "winget", "install", "--id", "GitHub.cli", "-e",
                "--source", "winget",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ], encoding="utf-8", errors="replace")
        except Exception:
            pass
        refresh_path()
        gh = find_gh()
        if gh:
            return gh

    try:
        api_url = "https://api.github.com/repos/cli/cli/releases/latest"
        req = urllib.request.Request(api_url, headers={"User-Agent": "vps-foryou"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        msi_url = None
        for a in data.get("assets", []):
            if a.get("name", "").endswith("_windows_amd64.msi"):
                msi_url = a.get("browser_download_url")
                break
        if not msi_url:
            return None
        tmp = os.path.join(tempfile.gettempdir(), "gh_cli_setup.msi")
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        urllib.request.urlretrieve(msi_url, tmp)
        if not install_msi(tmp):
            return None
        return wait_gh_file()
    except Exception:
        return None


def gh_status(gh):
    code, out, err = run_cmd([gh, "auth", "status"])
    return code == 0, out + "\n" + err


def has_scope(gh, scope):
    ok, text = gh_status(gh)
    return ok and scope in text.lower()


def ensure_login(gh):
    ok, _ = gh_status(gh)
    if ok:
        log("Already logged in.", GREEN)
    else:
        log("Not logged in. Browser login required.", YELLOW)
        try:
            subprocess.run([
                gh, "auth", "login", "--web", "--git-protocol", "https",
                "-s", "codespace", "-s", "repo", "-s", "workflow",
                "-s", "read:org", "-s", "gist",
            ], encoding="utf-8", errors="replace")
        except KeyboardInterrupt:
            return False
        ok, _ = gh_status(gh)
        if not ok:
            log("Login failed.", RED)
            return False
        log("Login successful.", GREEN)

    if not has_scope(gh, "codespace"):
        log("Missing 'codespace' scope. Refreshing token...", YELLOW)
        log("Browser will open, approve the request.", CYAN)
        try:
            subprocess.run([
                gh, "auth", "refresh", "-h", "github.com",
                "-s", "codespace", "-s", "repo", "-s", "workflow",
                "-s", "read:org", "-s", "gist",
            ], encoding="utf-8", errors="replace")
        except KeyboardInterrupt:
            return False
        if not has_scope(gh, "codespace"):
            log("Codespace scope still missing.", RED)
            return False
    else:
        log("Codespace scope present.", GREEN)
    return True


def load_cfg():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cfg(c):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=2)
    except Exception:
        pass


def gh_run(gh, cmd, silent=False):
    try:
        r = subprocess.run([gh] + cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception as e:
        if not silent:
            log("Command error: " + str(e), RED)
        return ""
    if r.returncode != 0:
        err = (r.stderr or "").strip()
        if err and not silent:
            log("stderr: " + err, RED)
        return ""
    return (r.stdout or "").strip()


def get_user(gh):
    out = gh_run(gh, ["api", "user", "--jq", ".login"], silent=True)
    return out.strip() if out else None


def repo_exists(gh, full):
    return bool(gh_run(gh, ["repo", "view", full, "--json", "name"], silent=True))


def create_repo(gh, full):
    log("Creating repo " + full + " ...", YELLOW)
    out = gh_run(gh, [
        "repo", "create", full, "--public", "--add-readme",
        "--description", "VPS FORYOU auto repo",
    ])
    return bool(out) or repo_exists(gh, full)


def resolve_repo(gh):
    user = get_user(gh)
    if not user:
        log("Could not detect username.", RED)
        return None
    log("Username: " + user, CYAN)

    cfg = load_cfg()
    saved = cfg.get("repo", "")
    if saved and saved.startswith(user + "/") and repo_exists(gh, saved):
        log("Saved repo: " + saved, GREEN)
        return saved

    full = user + "/" + DEFAULT_REPO_NAME
    if not repo_exists(gh, full):
        if not create_repo(gh, full):
            return None
    else:
        log("Repo exists: " + full, GREEN)
    cfg["repo"] = full
    save_cfg(cfg)
    return full


def list_codespaces(gh):
    out = gh_run(gh, ["codespace", "list", "--json",
                      "name,repository,state,machineName"], silent=True)
    if not out:
        return []
    try:
        return json.loads(out)
    except Exception:
        return []


def create_codespace(gh, repo):
    log("Creating Codespace (VPS) ...", YELLOW)
    name = gh_run(gh, [
        "codespace", "create",
        "-R", repo,
        "-m", "standardLinux32gb",
        "--idle-timeout", "60m",
        "--retention-period", "72h",
        "--display-name", "vps-foryou",
    ])
    if not name:
        return None
    return name.strip().splitlines()[-1].strip()


def run_remote_setup(gh, name):
    log("Installing tools inside VPS...", CYAN)
    setup_cmd = (
        "sudo apt-get update -qq && "
        "sudo apt-get install -y -qq python3-pip python3-venv git curl wget "
        "nano htop tmux net-tools ufw build-essential >/dev/null 2>&1; "
        "echo '=== VPS READY ==='; "
        "echo \"HOST: $(hostname)\"; "
        "echo \"USER: $(whoami)\"; "
        "echo \"OS:   $(. /etc/os-release; echo $PRETTY_NAME)\"; "
        "echo \"CPU:  $(nproc) cores\"; "
        "echo \"RAM:  $(free -h | awk '/Mem:/ {print $2}')\"; "
        "echo \"DISK: $(df -h / | awk 'NR==2 {print $2}')\"; "
        "echo \"IPv4: $(hostname -I | awk '{print $1}')\"; "
        "echo '================'"
    )
    try:
        r = subprocess.run(
            [gh, "codespace", "ssh", "-c", name, "--", "bash", "-c", setup_cmd],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=300,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        if out:
            return out
        if err:
            return err
    except Exception as e:
        log("Setup error: " + str(e), RED)
    return None


def open_ssh(gh, name):
    log("Opening SSH session...", GREEN)
    log("Type 'exit' to leave.", CYAN)
    try:
        subprocess.run([gh, "codespace", "ssh", "-c", name])
    except KeyboardInterrupt:
        pass


def main():
    print(BANNER, flush=True)
    log("VPS FORYOU starting...", GREEN)

    refresh_path()
    gh = find_gh()
    if gh:
        log("gh CLI: " + gh, GREEN)
    else:
        gh = install_gh()
        if not gh:
            log("Auto-install failed.", RED)
            input_line("Press Enter to exit...")
            sys.exit(1)
        log("gh CLI: " + gh, GREEN)

    if not ensure_login(gh):
        log("Cannot continue.", RED)
        input_line("Press Enter to exit...")
        sys.exit(1)

    repo = resolve_repo(gh)
    if not repo:
        input_line("Press Enter to exit...")
        sys.exit(1)

    log("Using repo: " + repo, GREEN)

    existing = list_codespaces(gh)
    reuse = None
    for cs in existing:
        if cs.get("repository") == repo and cs.get("state") in ("Available", "Shutdown"):
            reuse = cs.get("name")
            break

    if reuse:
        log("Found existing VPS: " + reuse, GREEN)
        ans = input_line("Reuse this VPS? (Y/n): ") or "y"
        if ans.lower() != "n":
            name = reuse
            if cs.get("state") == "Shutdown":
                log("Starting VPS...", CYAN)
                gh_run(gh, ["codespace", "start", "-c", name])
                time.sleep(8)
        else:
            name = create_codespace(gh, repo)
    else:
        name = create_codespace(gh, repo)

    if not name:
        log("Failed to create Codespace.", RED)
        input_line("Press Enter to exit...")
        sys.exit(1)

    log("VPS name: " + name, GREEN)
    log("Waiting for boot...", CYAN)
    time.sleep(8)

    info = run_remote_setup(gh, name)
    if info:
        print()
        for line in info.splitlines():
            print(CYAN + line + RESET)
        print()

    open_ssh(gh, name)

    log("SSH closed.", GREEN)
    log("Reconnect:  gh codespace ssh -c " + name, CYAN)
    log("Stop:       gh codespace stop -c " + name, CYAN)
    log("Delete:     gh codespace delete -c " + name + " --force", CYAN)
    input_line("Press Enter to exit...")


if __name__ == "__main__":
    main()