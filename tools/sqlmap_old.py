import json
import shlex
import subprocess
from typing import List, Dict, Any, Optional

from langchain.tools import tool as _lc_tool


# ----------------------------- helper: build cli args -----------------------
def build_sqlmap_cmd(
    params: Dict[str, Any], default_batch: bool = True, sqlmap_path: str = "sqlmap"
) -> List[str]:
    """
    Xây dựng list args cho sqlmap từ dict params.
    Thông số thường dùng (không giới hạn):
      - url (str)           -> -u
      - data (str)          -> --data
      - cookie (str)        -> --cookie
      - params (str)        -> -p
      - level (int)
      - risk (int)
      - threads (int)
      - proxy (str)
      - tor (bool)
      - timeout (int)
      - dbs/dump (bool)
      - extra_args (list or str)  -> được xử lý (nhưng sẽ bị lọc bởi blacklist)
    Trả về: list args (sẵn sàng dùng subprocess.run)
    """
    cmd = [sqlmap_path]

    if default_batch:
        cmd.append("--batch")

    if "url" in params and params["url"]:
        cmd += ["-u", str(params["url"])]

    if "data" in params and params["data"]:
        cmd += ["--data", str(params["data"])]

    if "cookie" in params and params["cookie"]:
        cmd += ["--cookie", str(params["cookie"])]

    if "params" in params and params["params"]:
        cmd += ["-p", str(params["params"])]

    if "level" in params:
        cmd += ["--level", str(int(params["level"]))]

    if "risk" in params:
        cmd += ["--risk", str(int(params["risk"]))]

    if "threads" in params:
        cmd += ["--threads", str(int(params["threads"]))]

    if "proxy" in params and params["proxy"]:
        cmd += ["--proxy", str(params["proxy"])]

    if params.get("tor"):
        cmd.append("--tor")

    if "timeout" in params:
        cmd += ["--timeout", str(int(params["timeout"]))]

    # boolean flags
    if params.get("dbs"):
        cmd.append("--dbs")
    if params.get("dump"):
        cmd.append("--dump")
    if params.get("exclude-sysdbs"):
        cmd.append("--exclude-sysdbs")
    if params.get("os-shell"):
        cmd.append("--os-shell")
    if params.get("os-pwn"):
        cmd.append("--os-pwn")

    # extra_args handled outside (so we can filter)
    extra = params.get("extra_args")
    if extra:
        if isinstance(extra, str):
            extra_list = shlex.split(extra)
        elif isinstance(extra, list):
            extra_list = [str(x) for x in extra]
        else:
            raise ValueError("extra_args must be list or string")
        cmd += extra_list

    return cmd


# ----------------------------- runner --------------------------------------
def run_sqlmap_with_cmd(
    cmd: List[str], timeout_sec: int = 600, stdout_cap: int = 20000
) -> Dict[str, Any]:
    """
    Thực thi sqlmap bằng subprocess (shell=False).
    Trả về dict chứa stdout/stderr/returncode và cmd.
    """
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout_sec, check=False
        )
        return {
            "ok": True,
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout[:stdout_cap],
            "stderr": proc.stderr[:stdout_cap],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Timeout after {timeout_sec}s", "cmd": cmd}
    except FileNotFoundError:
        return {
            "ok": False,
            "error": "sqlmap binary not found in PATH (or sqlmap_path incorrect).",
            "cmd": cmd,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "cmd": cmd}


# ------------------------ security: blacklist flags ------------------------
# LIST các flag nghiêm trọng muốn chặn (có thể mở rộng theo policy)
_DEFAULT_DANGEROUS_FLAGS = {
    "--os-shell",
    "--os-pwn",
    "--os-smbrelay",
    "--os-bof",
    "--priv-esc",
    "--os-cmd",
    "--msfvenom",
    "--os-smbrelay",
    "--os-smbexec",
}


def filter_args_against_blacklist(
    args: List[str], blacklist: Optional[set]
) -> List[str]:
    """
    Lọc danh sách args, loại bỏ các flag trong blacklist.
    Trả về danh sách args đã lọc.
    """
    if not blacklist:
        return args
    filtered = []
    i = 0
    while i < len(args):
        a = args[i]
        # nếu a exactly matches a blacklisted flag -> skip it (and skip possible next param if it's not another flag)
        if a in blacklist:
            # try to skip next token if it looks like a value (i+1 exists and doesn't start with '-')
            if i + 1 < len(args) and not str(args[i + 1]).startswith("-"):
                i += 2
            else:
                i += 1
            continue
        filtered.append(a)
        i += 1
    return filtered


# ------------------------ core: run from JSON params ------------------------
def run_sqlmap_from_json(
    params_json: str,
    timeout_sec: int = 600,
    sqlmap_path: str = "sqlmap",
    default_batch: bool = True,
    blacklist: Optional[set] = None,
) -> Dict[str, Any]:
    """
    Input: JSON string (top-level object) mô tả params (xem build_sqlmap_cmd).
    - blacklist: tập các flag nghiêm trọng sẽ bị loại trước khi chạy.
    - sqlmap_path: đường dẫn đến binary (mặc định 'sqlmap' trong PATH).
    Trả về dict chứa cmd/returncode/stdout/stderr hoặc error.
    """
    try:
        params = json.loads(params_json)
        if not isinstance(params, dict):
            raise ValueError("Top-level JSON must be an object/dict")
    except Exception as e:
        return {"ok": False, "error": f"Invalid JSON input: {e}"}

    try:
        # build raw cmd
        cmd = build_sqlmap_cmd(
            params, default_batch=default_batch, sqlmap_path=sqlmap_path
        )

        # apply blacklist filter to command (safer) - blacklist cũng sẽ so sánh cả các token trong extra_args
        effective_blacklist = (
            set(blacklist) if blacklist else set(_DEFAULT_DANGEROUS_FLAGS)
        )
        safe_cmd = [cmd[0]] + filter_args_against_blacklist(
            cmd[1:], effective_blacklist
        )

        # run
        result = run_sqlmap_with_cmd(safe_cmd, timeout_sec=timeout_sec)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------ REQUIRED: factory to create LangChain tool -------
def make_langchain_tool(
    name: str = "sqlmap_tool",
    description: Optional[str] = None,
    sqlmap_path: str = "sqlmap",
    default_batch: bool = True,
    blacklist: Optional[List[str]] = None,
):
    """
    BẮT BUỘC: trả về một LangChain tool đã decorate bằng @_lc_tool(...)
    - name: tên tool (string) - sẽ được truyền cho decorator
    - description: mô tả tool (nếu None, docstring mặc định sẽ dùng)
    - sqlmap_path: đường dẫn đến sqlmap binary
    - default_batch: luôn bật --batch nếu True
    - blacklist: list các flag sẽ bị chặn (ghi đè default)

    Usage:
        tool = make_langchain_tool()
        # pass 'tool' to your agent initialization
    """
    # chuẩn hoá blacklist
    blacklist_set = (
        set(blacklist) if blacklist is not None else _DEFAULT_DANGEROUS_FLAGS
    )

    # tạo tool function bên trong để decorator dùng variable runtime
    @_lc_tool(
        name, parse_docstring=True
    )  # docstring bên dưới sẽ được dùng như description nếu description=None
    def _sqlmap_tool(params_json: str) -> str:
        """
        Run sqlmap with JSON params. Input must be a JSON object string.

        Example input JSON:
        {
          "url": "http://127.0.0.1/vuln.php?id=1",
          "level": 3,
          "risk": 2,
          "threads": 4,
          "dbs": true,
          "extra_args": ["--flush-session", "--random-agent"]
        }

        Note: This tool WILL filter out dangerous flags (see default blacklist).
        """
        # If user provided a separate description for the tool, it's configured at decorator time.
        # Here we call the runner and return a JSON string (so tool returns a plain string).
        result = run_sqlmap_from_json(
            params_json,
            timeout_sec=600,
            sqlmap_path=sqlmap_path,
            default_batch=default_batch,
            blacklist=blacklist_set,
        )
        # Đồng nhất trả về string để tương thích tool calling (tool decorator có thể map type)
        return json.dumps(result, ensure_ascii=False)

    # Nếu caller muốn custom description (override docstring), LangChain decorator
    # hỗ trợ passing description khi tạo tool; vì decorator đã dùng parse_docstring=True,
    # nếu user muốn description khác, re-wrap không thuận tiện — caller có thể set tên và docstring ở đây.
    if description:
        # Một cách đơn giản: attach attribute __doc__ (note: decorator already ran, so this is best-effort)
        try:
            _sqlmap_tool.__doc__ = description
        except Exception:
            pass

    return _sqlmap_tool  # this is the decorated tool object


# ------------------------ example usage (để tham khảo) ---------------------
if __name__ == "__main__":
    # Demo: tạo tool và show cách gọi trực tiếp
    tool = make_langchain_tool(
        name="sqlmap_demo_tool", sqlmap_path="sqlmap", default_batch=True
    )

    # Agent/LLM sẽ truyền vào 1 JSON string. Ở đây ta gọi trực tiếp để test.
    demo_params = {
        "url": "http://127.0.0.1/vuln.php?id=1",
        "level": 3,
        "risk": 2,
        "threads": 2,
        "dbs": True,
        "extra_args": [
            "--flush-session",
            "--random-agent",
            "--os-shell",
        ],  # --os-shell sẽ bị loại bởi blacklist
    }

    # tool là object return từ decorator; gọi như một hàm thường (tool calling có thể khác tuỳ phiên bản)
    out = tool(json.dumps(demo_params))
    print("TOOL OUTPUT:", out)
