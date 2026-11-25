/* Coconut local offline syntax highlighter (VS Code token semantics, zero external dependencies). */
(function () {
  "use strict";

  const LANG_ALIASES = {
    js: "javascript",
    javascript: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    jsx: "jsx",
    ts: "typescript",
    typescript: "typescript",
    tsx: "tsx",
    py: "python",
    python: "python",
    pyw: "python",
    pyi: "python",
    java: "java",
    html: "html",
    htm: "html",
    xml: "xml",
    svg: "xml",
    xhtml: "xml",
    css: "css",
    scss: "css",
    less: "css",
    json: "json",
    jsonc: "json",
    jsonl: "json",
    yaml: "yaml",
    yml: "yaml",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
    shell: "bash",
    sql: "sql",
    c: "cpp",
    cpp: "cpp",
    "c++": "cpp",
    cc: "cpp",
    cxx: "cpp",
    h: "cpp",
    hpp: "cpp",
    rs: "rust",
    rust: "rust",
    go: "go",
    golang: "go",
    md: "markdown",
    markdown: "markdown",
    mdown: "markdown",
    mkd: "markdown",
    mkdn: "markdown",
    mdx: "markdown",
  };

  function words(str) {
    return new Set(str.trim().split(/\s+/).filter(Boolean));
  }

  const JS_KEYWORDS = words(
    "async await break case catch class const continue debugger default delete do else export extends finally for from function get if import in instanceof let new of return set static super switch throw try typeof var void while with yield"
  );
  const TS_EXTRA_KEYWORDS = words(
    "abstract as asserts declare enum implements infer interface is keyof module namespace never override package private protected public readonly Global satisfy satisfies type unique unknown"
  );
  const JS_LITERALS = words("true false null undefined NaN Infinity globalThis this arguments");
  const JS_TYPES = words(
    "Array Boolean Date Error Function JSON Map Math Number Object Promise Proxy Reflect RegExp Set String Symbol WeakMap WeakSet BigInt Int8Array Uint8Array Uint32Array Float64Array any boolean number string symbol void unknown never object"
  );

  const PY_KEYWORDS = words(
    "and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield match case"
  );
  const PY_LITERALS = words("True False None self cls Ellipsis NotImplemented");
  const PY_TYPES = words(
    "int float str bytes bool list tuple set frozenset dict type object Exception BaseException ValueError TypeError KeyError IndexError RuntimeError OSError Path Any Optional Union Callable Sequence Mapping Iterable Iterator"
  );
  const PY_BUILTINS = words(
    "abs all any ascii bin breakpoint callable chr classmethod compile complex delattr dir divmod enumerate eval exec filter format getattr globals hasattr hash help hex id input isinstance issubclass iter len locals map max memoryview min next oct open ord pow print property range repr reversed round setattr slice sorted staticmethod sum super vars zip __import__"
  );

  const JAVA_KEYWORDS = words(
    "abstract assert break case catch class const continue default do else enum exports extends final finally for goto if implements import instanceof interface module native new non-sealed open opens package permits private protected provides public record requires return sealed static strictfp super switch synchronized throw throws to transient transitive try uses var volatile while with yield"
  );
  const JAVA_LITERALS = words("true false null this");
  const JAVA_TYPES = words(
    "boolean byte char double float int long short void Boolean Byte Character Double Float Integer Long Short String Object Class List Map Set HashMap ArrayList Optional Stream CompletableFuture Exception RuntimeException Override Deprecated SuppressWarnings"
  );

  const CPP_KEYWORDS = words(
    "alignas alignof and and_eq asm auto bitand bitor break case catch class compl concept const consteval constexpr constinit const_cast continue co_await co_return co_yield decltype default delete do dynamic_cast else enum explicit export extern final for friend goto if inline mutable namespace new noexcept not not_eq operator or or_eq override private protected public register reinterpret_cast requires return sizeof static static_assert static_cast struct switch template this thread_local throw try typedef typeid typename union using virtual volatile while xor xor_eq"
  );
  const CPP_LITERALS = words("true false nullptr NULL");
  const CPP_TYPES = words(
    "bool char char8_t char16_t char32_t double float int long short signed unsigned void wchar_t size_t ssize_t int8_t int16_t int32_t int64_t uint8_t uint16_t uint32_t uint64_t intptr_t uintptr_t std string vector map unordered_map set unique_ptr shared_ptr optional variant string_view FILE"
  );

  const RUST_KEYWORDS = words(
    "as async await break const continue crate dyn else enum extern fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait type unsafe use where while"
  );
  const RUST_LITERALS = words("true false None Some Ok Err");
  const RUST_TYPES = words(
    "bool char f32 f64 i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize str String Vec Box Rc Arc Cell RefCell Option Result HashMap HashSet BTreeMap BTreeSet Pin Future Send Sync Copy Clone Debug Display Default"
  );

  const GO_KEYWORDS = words(
    "break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var"
  );
  const GO_LITERALS = words("true false nil iota");
  const GO_TYPES = words(
    "any bool byte comparable complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string uint uint8 uint16 uint32 uint64 uintptr"
  );
  const GO_BUILTINS = words(
    "append cap clear close complex copy delete imag len make max min new panic print println real recover"
  );

  const BASH_KEYWORDS = words(
    "if then else elif fi case esac for select while until do done in function time coproc declare typeset local export readonly unset shift return exit break continue trap eval exec source"
  );
  const BASH_BUILTINS = words(
    "echo printf read cd pwd pushd popd dirs let test set shopt alias unalias type hash bind help history jobs fg bg wait disown kill umask ulimit getopts"
  );

  const SQL_KEYWORDS = words(
    "ADD ALL ALTER AND ANY AS ASC AUTHORIZATION BACKUP BEGIN BETWEEN BREAK BROWSE BULK BY CASCADE CASE CHECK CHECKPOINT CLOSE CLUSTERED COALESCE COLLATE COLUMN COMMIT COMPUTE CONSTRAINT CONTAINS CONTAINSTABLE CONTINUE CONVERT CREATE CROSS CURRENT CURRENT_DATE CURRENT_TIME CURRENT_TIMESTAMP CURRENT_USER CURSOR DATABASE DBCC DEALLOCATE DECLARE DEFAULT DELETE DENY DESC DISK DISTINCT DISTRIBUTED DOUBLE DROP DUMP ELSE END ERRLVL ESCAPE EXCEPT EXEC EXECUTE EXISTS EXIT EXTERNAL FETCH FILE FILLFACTOR FOR FOREIGN FREETEXT FREETEXTTABLE FROM FULL FUNCTION GOTO GRANT GROUP HAVING HOLDLOCK IDENTITY IDENTITY_INSERT IDENTITYCOL IF IN INDEX INNER INSERT INTERSECT INTO IS JOIN KEY KILL LEFT LIKE LINENO LOAD MERGE NATIONAL NOCHECK NONCLUSTERED NOT NULL NULLIF OF OFF OFFSETS ON OPEN OPENDATASOURCE OPENQUERY OPENROWSET OPENXML OPTION OR ORDER OUTER OVER PERCENT PIVOT PLAN PRECISION PRIMARY PRINT PROC PROCEDURE PUBLIC RAISERROR READ READTEXT RECONFIGURE REFERENCES REPLICATION RESTORE RESTRICT RETURN REVERT REVOKE RIGHT ROLLBACK ROWCOUNT ROWGUIDCOL RULE SAVE SCHEMA SECURITYAUDIT SELECT SEMANTICKEYPHRASETABLE SEMANTICSIMILARITYDETAILSTABLE SEMANTICSIMILARITYTABLE SESSION_USER SET SETUSER SHUTDOWN SOME STATISTICS SYSTEM_USER TABLE TABLESAMPLE TEXTSIZE THEN TO TOP TRAN TRANSACTION TRIGGER TRUNCATE TRY_CONVERT TSEQUAL UNION UNIQUE UNPIVOT UPDATE UPDATETEXT USE USER VALUES VARYING VIEW WAITFOR WHEN WHERE WHILE WITH WITHIN GROUP WRITETEXT LIMIT OFFSET PRAGMA RETURNING CONFLICT DO NOTHING REPLACE EXPLAIN ANALYZE VACUUM"
  );
  const SQL_TYPES = words(
    "INT INTEGER SMALLINT TINYINT BIGINT DECIMAL NUMERIC FLOAT REAL DOUBLE PRECISION DATE TIME DATETIME TIMESTAMP CHAR VARCHAR TEXT NCHAR NVARCHAR NTEXT BINARY VARBINARY IMAGE BIT BOOLEAN BOOL BLOB JSON JSONB UUID SERIAL BIGSERIAL BYTEA"
  );

  const LANG_DEFS = {
    javascript: {
      keywords: JS_KEYWORDS,
      literals: JS_LITERALS,
      types: JS_TYPES,
      builtins: words("console window document Math JSON Object Array Promise Number String Boolean Symbol"),
      cStyleComments: true,
      hashComments: false,
      backtickStrings: true,
      jsxTags: false,
    },
    jsx: {
      keywords: JS_KEYWORDS,
      literals: JS_LITERALS,
      types: JS_TYPES,
      builtins: words("console window document React useState useEffect useMemo useCallback useRef"),
      cStyleComments: true,
      hashComments: false,
      backtickStrings: true,
      jsxTags: true,
    },
    typescript: {
      keywords: new Set([...JS_KEYWORDS, ...TS_EXTRA_KEYWORDS]),
      literals: JS_LITERALS,
      types: JS_TYPES,
      builtins: words("console window document Math JSON Object Array Promise Number String Boolean Symbol"),
      cStyleComments: true,
      hashComments: false,
      backtickStrings: true,
      jsxTags: false,
    },
    tsx: {
      keywords: new Set([...JS_KEYWORDS, ...TS_EXTRA_KEYWORDS]),
      literals: JS_LITERALS,
      types: JS_TYPES,
      builtins: words("console window document React useState useEffect useMemo useCallback useRef"),
      cStyleComments: true,
      hashComments: false,
      backtickStrings: true,
      jsxTags: true,
    },
    python: {
      keywords: PY_KEYWORDS,
      literals: PY_LITERALS,
      types: PY_TYPES,
      builtins: PY_BUILTINS,
      cStyleComments: false,
      hashComments: true,
      tripleStrings: true,
    },
    java: {
      keywords: JAVA_KEYWORDS,
      literals: JAVA_LITERALS,
      types: JAVA_TYPES,
      builtins: words("System Out Err Math Thread Collections Arrays Objects"),
      cStyleComments: true,
      hashComments: false,
    },
    cpp: {
      keywords: CPP_KEYWORDS,
      literals: CPP_LITERALS,
      types: CPP_TYPES,
      builtins: words("printf fprintf sprintf snprintf scanf cout cerr endl cin malloc calloc realloc free memcpy memset"),
      cStyleComments: true,
      hashComments: false,
      cppPreprocessor: true,
    },
    rust: {
      keywords: RUST_KEYWORDS,
      literals: RUST_LITERALS,
      types: RUST_TYPES,
      builtins: words("println print eprintln eprint format vec panic assert assert_eq assert_ne todo unimplemented dbg"),
      cStyleComments: true,
      hashComments: false,
      rustAttributes: true,
    },
    go: {
      keywords: GO_KEYWORDS,
      literals: GO_LITERALS,
      types: GO_TYPES,
      builtins: GO_BUILTINS,
      cStyleComments: true,
      hashComments: false,
      backtickStrings: true,
    },
    bash: {
      keywords: BASH_KEYWORDS,
      literals: words("true false"),
      types: new Set(),
      builtins: BASH_BUILTINS,
      cStyleComments: false,
      hashComments: true,
      shellVars: true,
    },
    sql: {
      keywords: SQL_KEYWORDS,
      literals: words("TRUE FALSE NULL"),
      types: SQL_TYPES,
      builtins: words("COUNT SUM AVG MIN MAX COALESCE NULLIF CAST EXTRACT SUBSTRING TRIM UPPER LOWER NOW"),
      cStyleComments: true,
      sqlComments: true,
      caseInsensitive: true,
    },
  };

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function wrapToken(cls, text) {
    if (!text) return "";
    if (!cls) return escapeHtml(text);
    // Split multi-line tokens so each line has balanced <span> tags
    if (text.indexOf("\n") !== -1) {
      return text
        .split("\n")
        .map((part) => (part ? '<span class="hljs-' + cls + '">' + escapeHtml(part) + "</span>" : ""))
        .join("\n");
    }
    return '<span class="hljs-' + cls + '">' + escapeHtml(text) + "</span>";
  }

  function highlightMarkup(code) {
    let out = "";
    let i = 0;
    const n = code.length;

    while (i < n) {
      if (code.startsWith("<!--", i)) {
        const end = code.indexOf("-->", i + 4);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 3);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      if (code.startsWith("<![CDATA[", i)) {
        const end = code.indexOf("]]>", i + 9);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 3);
        out += wrapToken("meta", slice);
        i += slice.length;
        continue;
      }
      if (code.startsWith("<!", i) || code.startsWith("<?", i)) {
        const end = code.indexOf(">", i + 2);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 1);
        out += wrapToken("meta", slice);
        i += slice.length;
        continue;
      }
      if (code[i] === "<" && /[A-Za-z\/!]/.test(code[i + 1] || "")) {
        const end = code.indexOf(">", i + 1);
        if (end !== -1) {
          const tagContent = code.slice(i, end + 1);
          out += highlightSingleTag(tagContent);
          i = end + 1;
          continue;
        }
      }
      const nextLt = code.indexOf("<", i + 1);
      const plain = nextLt === -1 ? code.slice(i) : code.slice(i, nextLt);
      out += escapeHtml(plain);
      i += plain.length;
    }
    return out;
  }

  function highlightSingleTag(tagStr) {
    const m = tagStr.match(/^(<\/?)([A-Za-z0-9_:-]+)([\s\S]*?)(\/?>)$/);
    if (!m) return wrapToken("tag", tagStr);
    const openSym = m[1];
    const tagName = m[2];
    const attrsPart = m[3];
    const closeSym = m[4];

    let attrOut = "";
    let lastIdx = 0;
    const attrRe = /([A-Za-z0-9_:@.-]+)(\s*=\s*)("[^"]*"|'[^']*'|[^\s"'>]+)?/g;
    let am;
    while ((am = attrRe.exec(attrsPart)) !== null) {
      if (am.index > lastIdx) {
        attrOut += escapeHtml(attrsPart.slice(lastIdx, am.index));
      }
      attrOut += wrapToken("attr", am[1]);
      if (am[2]) attrOut += escapeHtml(am[2]);
      if (am[3]) attrOut += wrapToken("string", am[3]);
      lastIdx = attrRe.lastIndex;
    }
    if (lastIdx < attrsPart.length) {
      attrOut += escapeHtml(attrsPart.slice(lastIdx));
    }

    return (
      wrapToken("punctuation", openSym) +
      wrapToken("tag", tagName) +
      attrOut +
      wrapToken("punctuation", closeSym)
    );
  }

  function highlightCss(code) {
    let out = "";
    let i = 0;
    const n = code.length;
    let inBlock = false;

    while (i < n) {
      if (code.startsWith("/*", i)) {
        const end = code.indexOf("*/", i + 2);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 2);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      const ch = code[i];
      if (ch === '"' || ch === "'") {
        let j = i + 1;
        while (j < n && code[j] !== ch) {
          if (code[j] === "\\") j++;
          j++;
        }
        const slice = code.slice(i, Math.min(n, j + 1));
        out += wrapToken("string", slice);
        i += slice.length;
        continue;
      }
      if (ch === "{") {
        inBlock = true;
        out += wrapToken("punctuation", "{");
        i++;
        continue;
      }
      if (ch === "}") {
        inBlock = false;
        out += wrapToken("punctuation", "}");
        i++;
        continue;
      }
      if (!inBlock) {
        const nextBrace = code.indexOf("{", i);
        const nextComment = code.indexOf("/*", i);
        let stop = n;
        if (nextBrace !== -1) stop = Math.min(stop, nextBrace);
        if (nextComment !== -1) stop = Math.min(stop, nextComment);
        if (stop > i) {
          const sel = code.slice(i, stop);
          out += sel.replace(/(@[A-Za-z_-]+)|([.#][A-Za-z0-9_-]+)|(:+[A-Za-z0-9_-]+)/g, (full, atRule, clsId, pseudo) => {
            if (atRule) return wrapToken("keyword", atRule);
            if (clsId) return wrapToken("type", clsId);
            if (pseudo) return wrapToken("function", pseudo);
            return escapeHtml(full);
          });
          i = stop;
          continue;
        }
      } else {
        const propMatch = code.slice(i).match(/^([A-Za-z-]+|--[A-Za-z0-9_-]+)(\s*:)/);
        if (propMatch) {
          out += wrapToken("attr", propMatch[1]) + wrapToken("punctuation", propMatch[2]);
          i += propMatch[0].length;
          continue;
        }
        const hexMatch = code.slice(i).match(/^#[0-9A-Fa-f]{3,8}\b/);
        if (hexMatch) {
          out += wrapToken("number", hexMatch[0]);
          i += hexMatch[0].length;
          continue;
        }
        const numMatch = code.slice(i).match(/^-?\d+(?:\.\d+)?(?:px|em|rem|ch|vh|vw|%|s|ms|deg|fr)?\b/);
        if (numMatch) {
          out += wrapToken("number", numMatch[0]);
          i += numMatch[0].length;
          continue;
        }
        const fnMatch = code.slice(i).match(/^([A-Za-z_-]+)(?=\()/);
        if (fnMatch) {
          out += wrapToken("function", fnMatch[1]);
          i += fnMatch[1].length;
          continue;
        }
      }
      out += escapeHtml(ch);
      i++;
    }
    return out;
  }

  function highlightJson(code) {
    let out = "";
    let i = 0;
    const n = code.length;

    while (i < n) {
      if (code.startsWith("//", i)) {
        const nl = code.indexOf("\n", i + 2);
        const slice = nl === -1 ? code.slice(i) : code.slice(i, nl);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      if (code.startsWith("/*", i)) {
        const end = code.indexOf("*/", i + 2);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 2);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      if (code[i] === '"') {
        let j = i + 1;
        while (j < n && code[j] !== '"') {
          if (code[j] === "\\") j++;
          j++;
        }
        const strSlice = code.slice(i, Math.min(n, j + 1));
        const rest = code.slice(Math.min(n, j + 1));
        const isKey = /^\s*:/.test(rest);
        out += wrapToken(isKey ? "attr" : "string", strSlice);
        i += strSlice.length;
        continue;
      }
      const numMatch = code.slice(i).match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b/);
      if (numMatch) {
        out += wrapToken("number", numMatch[0]);
        i += numMatch[0].length;
        continue;
      }
      const litMatch = code.slice(i).match(/^(?:true|false|null)\b/);
      if (litMatch) {
        out += wrapToken("literal", litMatch[0]);
        i += litMatch[0].length;
        continue;
      }
      out += escapeHtml(code[i]);
      i++;
    }
    return out;
  }

  function highlightYaml(code) {
    return code
      .split("\n")
      .map((line) => {
        if (/^\s*#/.test(line)) {
          return wrapToken("comment", line);
        }
        const keyMatch = line.match(/^(\s*(?:-\s+)?)([A-Za-z0-9_.-]+|"[^"]+"|'[^']+')(\s*:)([\s\S]*)$/);
        if (!keyMatch) {
          return highlightYamlValue(line);
        }
        return (
          escapeHtml(keyMatch[1]) +
          wrapToken("attr", keyMatch[2]) +
          wrapToken("punctuation", keyMatch[3]) +
          highlightYamlValue(keyMatch[4])
        );
      })
      .join("\n");
  }

  function highlightYamlValue(val) {
    let out = "";
    let i = 0;
    const n = val.length;
    while (i < n) {
      if (val[i] === "#" && (i === 0 || /\s/.test(val[i - 1]))) {
        out += wrapToken("comment", val.slice(i));
        break;
      }
      if (val[i] === '"' || val[i] === "'") {
        const ch = val[i];
        let j = i + 1;
        while (j < n && val[j] !== ch) {
          if (val[j] === "\\") j++;
          j++;
        }
        const s = val.slice(i, Math.min(n, j + 1));
        out += wrapToken("string", s);
        i += s.length;
        continue;
      }
      const lit = val.slice(i).match(/^(?:true|false|null|yes|no|on|off)\b/i);
      if (lit && (i === 0 || /[\s,\[\]{}]/.test(val[i - 1]))) {
        out += wrapToken("literal", lit[0]);
        i += lit[0].length;
        continue;
      }
      const num = val.slice(i).match(/^-?\d+(?:\.\d+)?\b/);
      if (num && (i === 0 || /[\s,\[\]{}]/.test(val[i - 1]))) {
        out += wrapToken("number", num[0]);
        i += num[0].length;
        continue;
      }
      out += escapeHtml(val[i]);
      i++;
    }
    return out;
  }

  function highlightGenericCode(code, def) {
    let out = "";
    let i = 0;
    const n = code.length;

    while (i < n) {
      // C-style line comment
      if (def.cStyleComments && code.startsWith("//", i)) {
        const nl = code.indexOf("\n", i + 2);
        const slice = nl === -1 ? code.slice(i) : code.slice(i, nl);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      // C-style block comment
      if (def.cStyleComments && code.startsWith("/*", i)) {
        const end = code.indexOf("*/", i + 2);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 2);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      // SQL -- comment
      if (def.sqlComments && code.startsWith("--", i)) {
        const nl = code.indexOf("\n", i + 2);
        const slice = nl === -1 ? code.slice(i) : code.slice(i, nl);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      // C/C++ preprocessor directive
      if (def.cppPreprocessor && code[i] === "#" && (i === 0 || code[i - 1] === "\n" || /^\s+$/.test(code.slice(code.lastIndexOf("\n", i - 1) + 1, i)))) {
        const nl = code.indexOf("\n", i + 1);
        const slice = nl === -1 ? code.slice(i) : code.slice(i, nl);
        out += wrapToken("meta", slice);
        i += slice.length;
        continue;
      }
      // Rust attribute #[...] or #![...]
      if (def.rustAttributes && (code.startsWith("#[", i) || code.startsWith("#![", i))) {
        const end = code.indexOf("]", i + 2);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 1);
        out += wrapToken("meta", slice);
        i += slice.length;
        continue;
      }
      // Hash comment (#)
      if (def.hashComments && code[i] === "#") {
        const nl = code.indexOf("\n", i + 1);
        const slice = nl === -1 ? code.slice(i) : code.slice(i, nl);
        out += wrapToken("comment", slice);
        i += slice.length;
        continue;
      }
      // Python triple-quoted strings
      if (def.tripleStrings && (code.startsWith('"""', i) || code.startsWith("'''", i))) {
        const delim = code.slice(i, i + 3);
        const end = code.indexOf(delim, i + 3);
        const slice = end === -1 ? code.slice(i) : code.slice(i, end + 3);
        out += wrapToken("string", slice);
        i += slice.length;
        continue;
      }
      // Single / double / backtick strings
      if (code[i] === '"' || code[i] === "'" || (def.backtickStrings && code[i] === "`")) {
        const quote = code[i];
        // In Rust, lifetime 'a is not a char literal if not closed by '
        if (def.rustAttributes && quote === "'") {
          const ltMatch = code.slice(i).match(/^'[a-zA-Z_][a-zA-Z0-9_]*\b(?!')/);
          if (ltMatch) {
            out += wrapToken("meta", ltMatch[0]);
            i += ltMatch[0].length;
            continue;
          }
        }
        let j = i + 1;
        while (j < n) {
          if (code[j] === "\\") {
            j += 2;
            continue;
          }
          if (code[j] === quote) {
            j++;
            break;
          }
          if (quote !== "`" && code[j] === "\n") {
            break;
          }
          j++;
        }
        const slice = code.slice(i, j);
        out += wrapToken("string", slice);
        i += slice.length;
        continue;
      }
      // Decorators / annotations (@decorator)
      if (code[i] === "@" && /[A-Za-z_]/.test(code[i + 1] || "")) {
        const decMatch = code.slice(i).match(/^@[A-Za-z_][A-Za-z0-9_.]*/);
        if (decMatch) {
          out += wrapToken("meta", decMatch[0]);
          i += decMatch[0].length;
          continue;
        }
      }
      // Shell variables ($VAR, ${VAR}, $1)
      if (def.shellVars && code[i] === "$") {
        const varMatch = code.slice(i).match(/^\$(?:\{[^}]+\}|[A-Za-z_][A-Za-z0-9_]*|[0-9@#?*!$-])/);
        if (varMatch) {
          out += wrapToken("attr", varMatch[0]);
          i += varMatch[0].length;
          continue;
        }
      }
      // JSX / TSX tag
      if (def.jsxTags && code[i] === "<" && /[A-Za-z\/]/.test(code[i + 1] || "")) {
        const tagMatch = code.slice(i).match(/^<\/?[A-Za-z][A-Za-z0-9_.]*/);
        if (tagMatch) {
          out += wrapToken("tag", tagMatch[0]);
          i += tagMatch[0].length;
          continue;
        }
      }
      // Numbers (hex, binary, octal, float, int)
      if (/\d/.test(code[i]) && (i === 0 || !/[A-Za-z0-9_$]/.test(code[i - 1]))) {
        const numMatch = code
          .slice(i)
          .match(/^(?:0[xX][0-9a-fA-F_]+|0[bB][01_]+|0[oO][0-7_]+|\d[\d_]*(?:\.[\d_]+)?(?:[eE][+-]?[\d_]+)?)[A-Za-z0-9_]*/);
        if (numMatch) {
          out += wrapToken("number", numMatch[0]);
          i += numMatch[0].length;
          continue;
        }
      }
      // Identifiers, keywords, types, functions
      if (/[A-Za-z_$]/.test(code[i])) {
        const idMatch = code.slice(i).match(/^[A-Za-z_$][A-Za-z0-9_$]*!?/);
        if (idMatch) {
          const word = idMatch[0];
          const lookup = def.caseInsensitive ? word.toUpperCase() : word;
          const after = code.slice(i + word.length);
          const isCall = /^\s*\(/.test(after);

          if (def.keywords && def.keywords.has(lookup)) {
            out += wrapToken("keyword", word);
          } else if (def.literals && def.literals.has(lookup)) {
            out += wrapToken("literal", word);
          } else if (def.types && def.types.has(lookup)) {
            out += wrapToken("type", word);
          } else if (def.builtins && def.builtins.has(lookup)) {
            out += wrapToken("built_in", word);
          } else if (/^[A-Z][A-Za-z0-9_]*$/.test(word) && !def.caseInsensitive) {
            out += wrapToken("type", word);
          } else if (isCall) {
            out += wrapToken("function", word);
          } else {
            out += escapeHtml(word);
          }
          i += word.length;
          continue;
        }
      }

      out += escapeHtml(code[i]);
      i++;
    }
    return out;
  }

  function highlightMarkdown(code) {
    let inFence = false;
    let fenceLang = "";
    return code
      .split("\n")
      .map((line) => {
        const fenceMatch = line.match(/^(\s*```+)([A-Za-z0-9_+-]*)(.*)$/);
        if (fenceMatch) {
          inFence = !inFence;
          fenceLang = inFence ? fenceMatch[2] || "" : "";
          return (
            wrapToken("meta", fenceMatch[1]) +
            wrapToken("type", fenceMatch[2]) +
            escapeHtml(fenceMatch[3])
          );
        }
        if (inFence) {
          return fenceLang ? highlightCodeString(line, fenceLang) : wrapToken("string", line);
        }
        if (/^\s*#{1,6}\s/.test(line)) {
          return wrapToken("keyword", line);
        }
        if (/^\s*>/.test(line)) {
          return wrapToken("comment", line);
        }
        if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
          return wrapToken("punctuation", line);
        }
        // Highlight inline code, bold, and markdown links without altering character positions
        let out = "";
        let i = 0;
        const n = line.length;
        const listPrefix = line.match(/^(\s*(?:[-*+]|\d+\.)\s+(?:\[[ xX]\]\s+)?)/);
        if (listPrefix) {
          out += wrapToken("meta", listPrefix[1]);
          i = listPrefix[1].length;
        }
        while (i < n) {
          if (line[i] === "`") {
            const end = line.indexOf("`", i + 1);
            if (end !== -1) {
              out += wrapToken("string", line.slice(i, end + 1));
              i = end + 1;
              continue;
            }
          }
          if (line.startsWith("**", i)) {
            const end = line.indexOf("**", i + 2);
            if (end !== -1) {
              out += wrapToken("function", line.slice(i, end + 2));
              i = end + 2;
              continue;
            }
          }
          if (line[i] === "[") {
            const linkMatch = line.slice(i).match(/^(\[[^\]]+\])(\([^)]+\))/);
            if (linkMatch) {
              out += wrapToken("attr", linkMatch[1]) + wrapToken("type", linkMatch[2]);
              i += linkMatch[0].length;
              continue;
            }
          }
          out += escapeHtml(line[i]);
          i++;
        }
        return out;
      })
      .join("\n");
  }

  function highlightCodeString(code, rawLang) {
    const cleanCode = String(code || "").replace(/\r\n/g, "\n");
    const normLang = LANG_ALIASES[String(rawLang || "").trim().toLowerCase()] || "";

    if (normLang === "markdown") {
      return highlightMarkdown(cleanCode);
    }
    if (normLang === "html" || normLang === "xml") {
      return highlightMarkup(cleanCode);
    }
    if (normLang === "css") {
      return highlightCss(cleanCode);
    }
    if (normLang === "json") {
      return highlightJson(cleanCode);
    }
    if (normLang === "yaml") {
      return highlightYaml(cleanCode);
    }
    if (normLang && LANG_DEFS[normLang]) {
      return highlightGenericCode(cleanCode, LANG_DEFS[normLang]);
    }
    return escapeHtml(cleanCode);
  }

  function highlightForEditor(code, rawLang) {
    const clean = String(code || "").replace(/\r\n/g, "\n");
    const html = highlightCodeString(clean, rawLang);
    // Trailing space after final newline keeps <pre> height synchronized with <textarea>
    return clean.endsWith("\n") ? html + " " : html;
  }

  function wrapLinesHtml(highlightedHtml, assignLineIds) {
    const rawLines = highlightedHtml.split("\n");
    // Drop single trailing empty line so we don't render an extra blank line number at the end
    if (rawLines.length > 1 && rawLines[rawLines.length - 1] === "") {
      rawLines.pop();
    }
    return rawLines
      .map((lineHtml, idx) => {
        const lineNum = idx + 1;
        const idAttr = assignLineIds ? ' id="L' + lineNum + '"' : "";
        const content = lineHtml.length > 0 ? lineHtml : " ";
        return (
          '<span class="code-line"' +
          idAttr +
          ' data-line="' +
          lineNum +
          '">' +
          content +
          "</span>"
        );
      })
      .join("\n");
  }

  function highlightElement(codeEl, explicitLang) {
    if (!codeEl || codeEl.getAttribute("data-highlighted") === "true") {
      return;
    }
    const rawLang =
      explicitLang ||
      codeEl.getAttribute("data-lang") ||
      (codeEl.className.match(/language-([A-Za-z0-9_+-]+)/) || [])[1] ||
      "";
    const isCodeFile = codeEl.getAttribute("data-code-file") === "true";
    const rawText = codeEl.textContent || "";
    // Store original text so Copy button copies pure source without line artefacts
    codeEl.setAttribute("data-raw-code", rawText);
    const highlighted = highlightCodeString(rawText, rawLang);
    codeEl.innerHTML = wrapLinesHtml(highlighted, isCodeFile);
    codeEl.setAttribute("data-highlighted", "true");
    codeEl.classList.add("hljs");
  }

  window.CocoHighlight = {
    LANG_ALIASES,
    highlightCodeString,
    highlightForEditor,
    highlightElement,
  };
})();
