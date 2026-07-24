var ue=(e,t)=>()=>(t||e((t={exports:{}}).exports,t),t.exports);var ke=ue((Ne,P)=>{var de=Object.defineProperty,l=(e,t)=>de(e,"name",{value:t,configurable:!0}),$=(e=>typeof require<"u"?require:typeof Proxy<"u"?new Proxy(e,{get:(t,r)=>(typeof require<"u"?require:t)[r]}):e)(function(e){if(typeof require<"u")return require.apply(this,arguments);throw new Error('Dynamic require of "'+e+'" is not supported')});function C(e){return!isNaN(parseFloat(e))&&isFinite(e)}l(C,"_isNumber");function y(e){return e.charAt(0).toUpperCase()+e.substring(1)}l(y,"_capitalize");function T(e){return function(){return this[e]}}l(T,"_getter");var E=["isConstructor","isEval","isNative","isToplevel"],S=["columnNumber","lineNumber"],k=["fileName","functionName","source"],fe=["args"],pe=["evalOrigin"],F=E.concat(S,k,fe,pe);function m(e){if(e)for(var t=0;t<F.length;t++)e[F[t]]!==void 0&&this["set"+y(F[t])](e[F[t]])}l(m,"StackFrame");m.prototype={getArgs:function(){return this.args},setArgs:function(e){if(Object.prototype.toString.call(e)!=="[object Array]")throw new TypeError("Args must be an Array");this.args=e},getEvalOrigin:function(){return this.evalOrigin},setEvalOrigin:function(e){if(e instanceof m)this.evalOrigin=e;else if(e instanceof Object)this.evalOrigin=new m(e);else throw new TypeError("Eval Origin must be an Object or StackFrame")},toString:function(){var e=this.getFileName()||"",t=this.getLineNumber()||"",r=this.getColumnNumber()||"",o=this.getFunctionName()||"";return this.getIsEval()?e?"[eval] ("+e+":"+t+":"+r+")":"[eval]:"+t+":"+r:o?o+" ("+e+":"+t+":"+r+")":e+":"+t+":"+r}};m.fromString=l(function(e){var t=e.indexOf("("),r=e.lastIndexOf(")"),o=e.substring(0,t),i=e.substring(t+1,r).split(","),n=e.substring(r+1);if(n.indexOf("@")===0)var a=/@(.+?)(?::(\d+))?(?::(\d+))?$/.exec(n,""),s=a[1],c=a[2],u=a[3];return new m({functionName:o,args:i||void 0,fileName:s,lineNumber:c||void 0,columnNumber:u||void 0})},"StackFrame$$fromString");for(b=0;b<E.length;b++)m.prototype["get"+y(E[b])]=T(E[b]),m.prototype["set"+y(E[b])]=function(e){return function(t){this[e]=!!t}}(E[b]);var b;for(w=0;w<S.length;w++)m.prototype["get"+y(S[w])]=T(S[w]),m.prototype["set"+y(S[w])]=function(e){return function(t){if(!C(t))throw new TypeError(e+" must be a Number");this[e]=Number(t)}}(S[w]);var w;for(_=0;_<k.length;_++)m.prototype["get"+y(k[_])]=T(k[_]),m.prototype["set"+y(k[_])]=function(e){return function(t){this[e]=String(t)}}(k[_]);var _,R=m;function W(){var e=/^\s*at .*(\S+:\d+|\(native\))/m,t=/^(eval@)?(\[native code])?$/;return{parse:l(function(r){if(r.stack&&r.stack.match(e))return this.parseV8OrIE(r);if(r.stack)return this.parseFFOrSafari(r);throw new Error("Cannot parse given Error object")},"ErrorStackParser$$parse"),extractLocation:l(function(r){if(r.indexOf(":")===-1)return[r];var o=/(.+?)(?::(\d+))?(?::(\d+))?$/,i=o.exec(r.replace(/[()]/g,""));return[i[1],i[2]||void 0,i[3]||void 0]},"ErrorStackParser$$extractLocation"),parseV8OrIE:l(function(r){var o=r.stack.split(`
`).filter(function(i){return!!i.match(e)},this);return o.map(function(i){i.indexOf("(eval ")>-1&&(i=i.replace(/eval code/g,"eval").replace(/(\(eval at [^()]*)|(,.*$)/g,""));var n=i.replace(/^\s+/,"").replace(/\(eval code/g,"(").replace(/^.*?\s+/,""),a=n.match(/ (\(.+\)$)/);n=a?n.replace(a[0],""):n;var s=this.extractLocation(a?a[1]:n),c=a&&n||void 0,u=["eval","<anonymous>"].indexOf(s[0])>-1?void 0:s[0];return new R({functionName:c,fileName:u,lineNumber:s[1],columnNumber:s[2],source:i})},this)},"ErrorStackParser$$parseV8OrIE"),parseFFOrSafari:l(function(r){var o=r.stack.split(`
`).filter(function(i){return!i.match(t)},this);return o.map(function(i){if(i.indexOf(" > eval")>-1&&(i=i.replace(/ line (\d+)(?: > eval line \d+)* > eval:\d+:\d+/g,":$1")),i.indexOf("@")===-1&&i.indexOf(":")===-1)return new R({functionName:i});var n=/((.*".+"[^@]*)?[^@]*)(?:@)/,a=i.match(n),s=a&&a[1]?a[1]:void 0,c=this.extractLocation(i.replace(n,""));return new R({functionName:s,fileName:c[0],lineNumber:c[1],columnNumber:c[2],source:i})},this)},"ErrorStackParser$$parseFFOrSafari")}}l(W,"ErrorStackParser");var me=new W,he=me,h=typeof process=="object"&&typeof process.versions=="object"&&typeof process.versions.node=="string"&&!process.browser,H=h&&typeof P<"u"&&typeof P.exports<"u"&&typeof $<"u"&&typeof __dirname<"u",ye=h&&!H,ge=typeof Deno<"u",q=!h&&!ge,be=q&&typeof window=="object"&&typeof document=="object"&&typeof document.createElement=="function"&&"sessionStorage"in window&&typeof importScripts!="function",we=q&&typeof importScripts=="function"&&typeof self=="object";typeof navigator=="object"&&typeof navigator.userAgent=="string"&&navigator.userAgent.indexOf("Chrome")==-1&&navigator.userAgent.indexOf("Safari")>-1;var z,L,B,U,D;async function j(){if(!h||(z=(await import("./__vite-browser-external-9wXp6ZBx.js")).default,U=await import("./__vite-browser-external-9wXp6ZBx.js"),D=await import("./__vite-browser-external-9wXp6ZBx.js"),B=(await import("./__vite-browser-external-9wXp6ZBx.js")).default,L=await import("./__vite-browser-external-9wXp6ZBx.js"),A=L.sep,typeof $<"u"))return;let e=U,t=await import("./__vite-browser-external-9wXp6ZBx.js"),r=await import("./__vite-browser-external-9wXp6ZBx.js"),o=await import("./__vite-browser-external-9wXp6ZBx.js"),i={fs:e,crypto:t,ws:r,child_process:o};globalThis.require=function(n){return i[n]}}l(j,"initNodeModules");function V(e,t){return L.resolve(t||".",e)}l(V,"node_resolvePath");function Y(e,t){return t===void 0&&(t=location),new URL(e,t).toString()}l(Y,"browser_resolvePath");var I;h?I=V:I=Y;var A;h||(A="/");function X(e,t){return e.startsWith("file://")&&(e=e.slice(7)),e.includes("://")?{response:fetch(e)}:{binary:D.readFile(e).then(r=>new Uint8Array(r.buffer,r.byteOffset,r.byteLength))}}l(X,"node_getBinaryResponse");function J(e,t){let r=new URL(e,location);return{response:fetch(r,t?{integrity:t}:{})}}l(J,"browser_getBinaryResponse");var O;h?O=X:O=J;async function K(e,t){let{response:r,binary:o}=O(e,t);if(o)return o;let i=await r;if(!i.ok)throw new Error(`Failed to load '${e}': request failed.`);return new Uint8Array(await i.arrayBuffer())}l(K,"loadBinaryFile");var N;if(be)N=l(async e=>await import(e),"loadScript");else if(we)N=l(async e=>{try{globalThis.importScripts(e)}catch(t){if(t instanceof TypeError)await import(e);else throw t}},"loadScript");else if(h)N=G;else throw new Error("Cannot determine runtime environment");async function G(e){e.startsWith("file://")&&(e=e.slice(7)),e.includes("://")?B.runInThisContext(await(await fetch(e)).text()):await import(z.pathToFileURL(e).href)}l(G,"nodeLoadScript");async function Q(e){if(h){await j();let t=await D.readFile(e,{encoding:"utf8"});return JSON.parse(t)}else return await(await fetch(e)).json()}l(Q,"loadLockFile");async function Z(){if(H)return __dirname;let e;try{throw new Error}catch(o){e=o}let t=he.parse(e)[0].fileName;if(h&&!t.startsWith("file://")&&(t=`file://${t}`),ye){let o=await import("./__vite-browser-external-9wXp6ZBx.js");return(await import("./__vite-browser-external-9wXp6ZBx.js")).fileURLToPath(o.dirname(t))}let r=t.lastIndexOf(A);if(r===-1)throw new Error("Could not extract indexURL path from pyodide module location");return t.slice(0,r)}l(Z,"calculateDirname");function ee(e){let t=e.FS,r=e.FS.filesystems.MEMFS,o=e.PATH,i={DIR_MODE:16895,FILE_MODE:33279,mount:function(n){if(!n.opts.fileSystemHandle)throw new Error("opts.fileSystemHandle is required");return r.mount.apply(null,arguments)},syncfs:async(n,a,s)=>{try{let c=i.getLocalSet(n),u=await i.getRemoteSet(n),d=a?u:c,p=a?c:u;await i.reconcile(n,d,p),s(null)}catch(c){s(c)}},getLocalSet:n=>{let a=Object.create(null);function s(d){return d!=="."&&d!==".."}l(s,"isRealDir");function c(d){return p=>o.join2(d,p)}l(c,"toAbsolute");let u=t.readdir(n.mountpoint).filter(s).map(c(n.mountpoint));for(;u.length;){let d=u.pop(),p=t.stat(d);t.isDir(p.mode)&&u.push.apply(u,t.readdir(d).filter(s).map(c(d))),a[d]={timestamp:p.mtime,mode:p.mode}}return{type:"local",entries:a}},getRemoteSet:async n=>{let a=Object.create(null),s=await _e(n.opts.fileSystemHandle);for(let[c,u]of s)c!=="."&&(a[o.join2(n.mountpoint,c)]={timestamp:u.kind==="file"?(await u.getFile()).lastModifiedDate:new Date,mode:u.kind==="file"?i.FILE_MODE:i.DIR_MODE});return{type:"remote",entries:a,handles:s}},loadLocalEntry:n=>{let a=t.lookupPath(n).node,s=t.stat(n);if(t.isDir(s.mode))return{timestamp:s.mtime,mode:s.mode};if(t.isFile(s.mode))return a.contents=r.getFileDataAsTypedArray(a),{timestamp:s.mtime,mode:s.mode,contents:a.contents};throw new Error("node type not supported")},storeLocalEntry:(n,a)=>{if(t.isDir(a.mode))t.mkdirTree(n,a.mode);else if(t.isFile(a.mode))t.writeFile(n,a.contents,{canOwn:!0});else throw new Error("node type not supported");t.chmod(n,a.mode),t.utime(n,a.timestamp,a.timestamp)},removeLocalEntry:n=>{var a=t.stat(n);t.isDir(a.mode)?t.rmdir(n):t.isFile(a.mode)&&t.unlink(n)},loadRemoteEntry:async n=>{if(n.kind==="file"){let a=await n.getFile();return{contents:new Uint8Array(await a.arrayBuffer()),mode:i.FILE_MODE,timestamp:a.lastModifiedDate}}else{if(n.kind==="directory")return{mode:i.DIR_MODE,timestamp:new Date};throw new Error("unknown kind: "+n.kind)}},storeRemoteEntry:async(n,a,s)=>{let c=n.get(o.dirname(a)),u=t.isFile(s.mode)?await c.getFileHandle(o.basename(a),{create:!0}):await c.getDirectoryHandle(o.basename(a),{create:!0});if(u.kind==="file"){let d=await u.createWritable();await d.write(s.contents),await d.close()}n.set(a,u)},removeRemoteEntry:async(n,a)=>{await n.get(o.dirname(a)).removeEntry(o.basename(a)),n.delete(a)},reconcile:async(n,a,s)=>{let c=0,u=[];Object.keys(a.entries).forEach(function(f){let g=a.entries[f],x=s.entries[f];(!x||t.isFile(g.mode)&&g.timestamp.getTime()>x.timestamp.getTime())&&(u.push(f),c++)}),u.sort();let d=[];if(Object.keys(s.entries).forEach(function(f){a.entries[f]||(d.push(f),c++)}),d.sort().reverse(),!c)return;let p=a.type==="remote"?a.handles:s.handles;for(let f of u){let g=o.normalize(f.replace(n.mountpoint,"/")).substring(1);if(s.type==="local"){let x=p.get(g),ce=await i.loadRemoteEntry(x);i.storeLocalEntry(f,ce)}else{let x=i.loadLocalEntry(f);await i.storeRemoteEntry(p,g,x)}}for(let f of d)if(s.type==="local")i.removeLocalEntry(f);else{let g=o.normalize(f.replace(n.mountpoint,"/")).substring(1);await i.removeRemoteEntry(p,g)}}};e.FS.filesystems.NATIVEFS_ASYNC=i}l(ee,"initializeNativeFS");var _e=l(async e=>{let t=[];async function r(i){for await(let n of i.values())t.push(n),n.kind==="directory"&&await r(n)}l(r,"collect"),await r(e);let o=new Map;o.set(".",e);for(let i of t){let n=(await e.resolve(i)).join("/");o.set(n,i)}return o},"getFsHandles");function te(e){let t={noImageDecoding:!0,noAudioDecoding:!0,noWasmDecoding:!1,preRun:oe(e),quit(r,o){throw t.exited={status:r,toThrow:o},o},print:e.stdout,printErr:e.stderr,arguments:e.args,API:{config:e},locateFile:r=>e.indexURL+r,instantiateWasm:se(e.indexURL)};return t}l(te,"createSettings");function ne(e){return function(t){let r="/";try{t.FS.mkdirTree(e)}catch(o){console.error(`Error occurred while making a home directory '${e}':`),console.error(o),console.error(`Using '${r}' for a home directory instead`),e=r}t.FS.chdir(e)}}l(ne,"createHomeDirectory");function re(e){return function(t){Object.assign(t.ENV,e)}}l(re,"setEnvironment");function ae(e){return t=>{for(let r of e)t.FS.mkdirTree(r),t.FS.mount(t.FS.filesystems.NODEFS,{root:r},r)}}l(ae,"mountLocalDirectories");function ie(e){let t=K(e);return r=>{let o=r._py_version_major(),i=r._py_version_minor();r.FS.mkdirTree("/lib"),r.FS.mkdirTree(`/lib/python${o}.${i}/site-packages`),r.addRunDependency("install-stdlib"),t.then(n=>{r.FS.writeFile(`/lib/python${o}${i}.zip`,n)}).catch(n=>{console.error("Error occurred while installing the standard library:"),console.error(n)}).finally(()=>{r.removeRunDependency("install-stdlib")})}}l(ie,"installStdlib");function oe(e){let t;return e.stdLibURL!=null?t=e.stdLibURL:t=e.indexURL+"python_stdlib.zip",[ie(t),ne(e.env.HOME),re(e.env),ae(e._node_mounts),ee]}l(oe,"getFileSystemInitializationFuncs");function se(e){if(typeof WasmOffsetConverter<"u")return;let{binary:t,response:r}=O(e+"pyodide.asm.wasm");return function(o,i){return async function(){try{let n;r?n=await WebAssembly.instantiateStreaming(r,o):n=await WebAssembly.instantiate(await t,o);let{instance:a,module:s}=n;i(a,s)}catch(n){console.warn("wasm instantiation failed!"),console.warn(n)}}(),{}}}l(se,"getInstantiateWasmFunc");var M="0.27.2";async function le(e={}){var t,r;await j();let o=e.indexURL||await Z();o=I(o),o.endsWith("/")||(o+="/"),e.indexURL=o;let i={fullStdLib:!1,jsglobals:globalThis,stdin:globalThis.prompt?globalThis.prompt:void 0,lockFileURL:o+"pyodide-lock.json",args:[],_node_mounts:[],env:{},packageCacheDir:o,packages:[],enableRunUntilComplete:!1,checkAPIVersion:!0,BUILD_ID:"f88dc4abb40ec8e780c94a5f70bcef45ec9eb3c1aee1c99da527febfef1c6f3f"},n=Object.assign(i,e);(t=n.env).HOME??(t.HOME="/home/pyodide"),(r=n.env).PYTHONINSPECT??(r.PYTHONINSPECT="1");let a=te(n),s=a.API;if(s.lockFilePromise=Q(n.lockFileURL),typeof _createPyodideModule!="function"){let f=`${n.indexURL}pyodide.asm.js`;await N(f)}let c;if(e._loadSnapshot){let f=await e._loadSnapshot;ArrayBuffer.isView(f)?c=f:c=new Uint8Array(f),a.noInitialRun=!0,a.INITIAL_MEMORY=c.length}let u=await _createPyodideModule(a);if(a.exited)throw a.exited.toThrow;if(e.pyproxyToStringRepr&&s.setPyProxyToStringMethod(!0),s.version!==M&&n.checkAPIVersion)throw new Error(`Pyodide version does not match: '${M}' <==> '${s.version}'. If you updated the Pyodide version, make sure you also updated the 'indexURL' parameter passed to loadPyodide.`);u.locateFile=f=>{throw new Error("Didn't expect to load any more file_packager files!")};let d;c&&(d=s.restoreSnapshot(c));let p=s.finalizeBootstrap(d,e._snapshotDeserializer);return s.sys.path.insert(0,s.config.env.HOME),p.version.includes("dev")||s.setCdnUrl(`https://cdn.jsdelivr.net/pyodide/v${p.version}/full/`),s._pyodide.set_excepthook(),await s.packageIndexReady,s.initializeStreams(n.stdin,n.stdout,n.stderr),p}l(le,"loadPyodide");var ve=`"""Shared test harness for CodeJourney.

This file is the single source of truth for how student code is executed and
graded. It runs in TWO places, unmodified:

  1. In the browser, under Pyodide, when a student hits "Run".
  2. On the server, inside the sandbox container, when a student hits "Submit".

Keeping one file for both is deliberate. If the run path and the submit path
could disagree, a student would see green on Run and red on Submit, and the
platform's core promise -- that failure is explainable -- would break at exactly
the moment it is being tested. Any divergence is a platform incident, not a
student error. See docs/architecture.md, "The divergence rule".

Constraints, because this runs under Pyodide:
  - stdlib only, and only modules Pyodide ships
  - no threading, no subprocess, no signal-based timeouts
  - no I/O other than what the caller injects

Timeouts are NOT enforced here. The browser enforces them by running Pyodide in
a Web Worker and terminating it; the server enforces them with \`timeout\` in the
container. Enforcing them differently is fine -- the *grading* is what must match.
"""

import copy
import io
import sys
import traceback

# The filename student code is compiled under. Appears in tracebacks, so it must
# be identical in both environments or error messages will differ.
STUDENT_FILENAME = "main.py"

MAX_REPR = 300


def _safe_repr(value):
    """repr() that can't itself blow up the harness or flood the UI."""
    try:
        text = repr(value)
    except BaseException:
        return f"<unreprable {type(value).__name__}>"
    if len(text) > MAX_REPR:
        return text[: MAX_REPR - 3] + "..."
    return text


def _student_line(exc):
    """Find the line number in the student's own file, ignoring harness frames.

    Novices need the line *they* wrote, not the innermost frame, which may be
    deep inside a stdlib call they've never heard of.
    """
    line = None
    for frame in traceback.extract_tb(exc.__traceback__):
        if frame.filename == STUDENT_FILENAME:
            line = frame.lineno
    return line


def _format_exception(exc):
    """Structured error info. The error-translation table (Week 4) consumes this.

    We return the raw pieces rather than a rendered string so the translator can
    pattern-match on \`type\` and \`message\` without re-parsing a traceback.
    """
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "line": _student_line(exc),
        # Full traceback is kept for the instructor view and the report, but the
        # student UI should render the translation, not this.
        "traceback": "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ),
    }


def _load(source):
    """Exec student source into a fresh namespace.

    Returns (namespace, error). Syntax errors surface here, before any test runs.
    """
    namespace = {"__name__": "__main__", "__file__": STUDENT_FILENAME}
    stdout = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = stdout
        code = compile(source, STUDENT_FILENAME, "exec")
        exec(code, namespace)
    except BaseException as exc:
        return None, _format_exception(exc), stdout.getvalue()
    finally:
        sys.stdout = real_stdout
    return namespace, None, stdout.getvalue()


def run_tests(source, entrypoint, tests):
    """Execute \`source\` and run \`tests\` against its \`entrypoint\` function.

    Args:
        source: the student's code, as a string.
        entrypoint: name of the function the tests call, e.g. "overdue_goals".
        tests: list of dicts, each with:
            name:     human-readable label, shown to the student
            args:     list of positional args to pass
            expected: the value the function should return
            hidden:   if True, the student sees pass/fail but not the args.
                      Hidden tests exist so exercises can't be gamed by
                      hardcoding, not to be mysterious -- keep at least one
                      visible test per exercise or feedback becomes unactionable.

    Returns a dict the frontend and the Submission row both consume directly:
        {
          "phase":  "loaded" | "syntax_error" | "missing_entrypoint",
          "error":  {type, message, line, traceback} | None,
          "stdout": str,            # printed at import time
          "tests":  [ {...}, ... ],
          "passed": bool,           # all tests passed
          "summary": {passed, total}
        }
    """
    namespace, error, import_stdout = _load(source)

    if error is not None:
        return {
            "phase": "syntax_error",
            "error": error,
            "stdout": import_stdout,
            "tests": [],
            "passed": False,
            "summary": {"passed": 0, "total": len(tests)},
        }

    function = namespace.get(entrypoint)
    if not callable(function):
        return {
            "phase": "missing_entrypoint",
            "error": {
                "type": "MissingFunction",
                "message": (
                    f"This exercise expects a function called {entrypoint!r}, "
                    "but it isn't defined yet."
                ),
                "line": None,
                "traceback": "",
            },
            "stdout": import_stdout,
            "tests": [],
            "passed": False,
            "summary": {"passed": 0, "total": len(tests)},
        }

    results = []
    for test in tests:
        results.append(_run_one(function, test))

    passed_count = sum(1 for r in results if r["status"] == "pass")
    return {
        "phase": "loaded",
        "error": None,
        "stdout": import_stdout,
        "tests": results,
        "passed": passed_count == len(results) and len(results) > 0,
        "summary": {"passed": passed_count, "total": len(results)},
    }


def _run_one(function, test):
    hidden = test.get("hidden", False)
    # deepcopy so a student mutating an argument can't corrupt later tests --
    # otherwise test 3 fails because of test 2 and the feedback is a lie.
    args = copy.deepcopy(test.get("args", []))
    expected = test.get("expected")

    stdout = io.StringIO()
    real_stdout = sys.stdout
    try:
        sys.stdout = stdout
        actual = function(*args)
    except BaseException as exc:
        sys.stdout = real_stdout
        return {
            "name": test.get("name", "test"),
            "status": "error",
            "hidden": hidden,
            "args": None if hidden else _safe_repr(args),
            "expected": None if hidden else _safe_repr(expected),
            "actual": None,
            "stdout": stdout.getvalue(),
            "error": _format_exception(exc),
        }
    finally:
        sys.stdout = real_stdout

    ok = _compare(actual, expected)
    return {
        "name": test.get("name", "test"),
        "status": "pass" if ok else "fail",
        "hidden": hidden,
        "args": None if hidden else _safe_repr(args),
        "expected": None if hidden else _safe_repr(expected),
        "actual": None if (hidden and not ok) else _safe_repr(actual),
        "stdout": stdout.getvalue(),
        "error": None,
    }


def _compare(actual, expected):
    """Equality with a float tolerance.

    Floats are compared with a tolerance because CPython and Pyodide can differ
    in the last bits on some operations, and because a novice computing a mean
    should not fail on 3.3333333333333335 != 3.3333333333333330. Exercises
    needing exact float equality should assert on a rounded value instead.
    """
    if isinstance(expected, float) and isinstance(actual, (int, float)):
        if isinstance(actual, bool):
            return False
        return abs(actual - expected) < 1e-9
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return False
        return all(_compare(a, e) for a, e in zip(actual, expected))
    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_compare(actual[k], expected[k]) for k in expected)
    # bool/int: Python says True == 1. For a novice returning True where 1 is
    # expected, that's a real mistake worth surfacing, so compare types too.
    if isinstance(expected, bool) != isinstance(actual, bool):
        return False
    return actual == expected
`;const xe="0.27.2",Ee=`https://cdn.jsdelivr.net/pyodide/v${xe}/full/`;let v=null;async function Se(){return v||(v=await le({indexURL:Ee}),v.FS.mkdirTree("/harness"),v.FS.writeFile("/harness/harness.py",ve),v.runPython('import sys; sys.path.insert(0, "/harness")'),v)}self.onmessage=async e=>{const{id:t,source:r,entrypoint:o,tests:i}=e.data;try{const n=await Se();n.globals.set("__cj_source",r),n.globals.set("__cj_entrypoint",o),n.globals.set("__cj_tests",n.toPy(i));const a=n.runPython(`
import json, harness
json.dumps(harness.run_tests(__cj_source, __cj_entrypoint, __cj_tests.to_py()))
`);self.postMessage({id:t,ok:!0,result:JSON.parse(a)})}catch(n){self.postMessage({id:t,ok:!1,error:n instanceof Error?n.message:String(n)})}}});export default ke();
