"""Map changed files to the review axes (references/axes/*.md) a reviewer should load.

An axis holds the checks that matter only for some kinds of code: web requests,
caches, messaging, money and so on. A file selects an axis by where it lives
(path rules, as in detect_languages.py) or by what it contains (signals: imports,
API names and keywords typical of that kind of code).

Signals are deliberately broad. Loading an axis that turns out not to apply costs
a few hundred tokens; missing one drops a whole class of checks from the review.
The reviewer can also load any axis from the SKILL.md index that the detector
did not select, so a signal list is a starting point, not the last word.

Standard library only. File contents are read by the caller (detect_languages.py)
under its own rules for symlinks and pinned revisions; nothing here touches disk.
"""

from __future__ import annotations

import codecs
import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

AXES_DIR = Path(__file__).resolve().parent.parent / "references" / "axes"

# Read at most this much of each file when looking for signals.
MAX_SCAN_BYTES = 512 * 1024


@dataclass(frozen=True)
class Axis:
    """One axis file and the evidence that selects it.

    paths:     "dir/" (a directory of that name at any depth) or a lowercase basename glob.
    languages: language references (detect_languages.py) that select this axis on their own.
    signals:   regular expressions searched in the file's text, case-insensitively and
               with ^/$ matching at line boundaries.
    """
    name: str
    paths: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    signals: tuple[str, ...] = ()
    pattern: re.Pattern | None = field(default=None, compare=False, repr=False)


_ROUTE_DECORATOR = r"@\w+\.(?:route|get|post|put|delete|patch)\s*\("

_AXES: list[Axis] = [
    Axis(
        "web",
        paths=("routes/", "controllers/", "handlers/", "middleware/", "middlewares/", "urls.py", "routes.rb",
               "*_controller.rb", "*controller.cs", "*controller.java", "*controller.kt", "*.controller.ts"),
        signals=(
            r"\b(?:flask|django|fastapi|starlette|aiohttp|tornado|bottle|sanic|falcon|express|koa|fastify|hono"
            r"|@nestjs|next/server|net/http|gin-gonic|labstack/echo|gofiber|go-chi|gorilla/mux|actix[-_]web|axum"
            r"|rocket|warp|sinatra|laravel|symfony|vapor|aspnetcore|servlet)\b",
            r"@(?:Rest)?Controller\b|@(?:Get|Post|Put|Delete|Patch|Request)Mapping\b",
            r"\[(?:ApiController|Http(?:Get|Post|Put|Delete|Patch))\b|\bMap(?:Get|Post|Put|Delete|Patch)\s*\(",
            r"\bActionController\b|\bRoute::|http\.ResponseWriter|\bHandleFunc\b",
            _ROUTE_DECORATOR, r"\brouter\.(?:get|post|put|delete|patch|use)\s*\(",
            r"\bres\.(?:cookie|send|json|status|redirect)\s*\(|\brequest\.(?:form|args|cookies|get_json|json)\b",
            r"\bset[-_]?cookie\b|\bcsrf|\bcors\b|samesite|access-control-allow",
        ),
    ),
    Axis(
        "caching",
        signals=(
            r"\bcach(?:e|ed|es|ing)\b", r"\bmemoi[sz]", r"\blru_cache\b", r"@cacheable\b",
            r"\bredis\b", r"\bmemcache", r"\bIMemoryCache\b|\bIDistributedCache\b",
            r"cache-control", r"\bmax-age\b", r"['\"]vary['\"]", r"\btenant",
        ),
    ),
    Axis(
        "messaging",
        signals=(
            r"\b(?:kafka|rabbitmq|amqp|pika|celery|sqs|sns|eventbridge|kinesis|pubsub|nats|nsq|bullmq|sidekiq"
            r"|resque|dramatiq|masstransit|nservicebus|servicebus|activemq|pulsar|webhooks?|outbox|idempoten\w*)\b",
            r"\bdead[-_ ]?letter", r"@(?:Kafka|Rabbit|Jms|Sqs)Listener\b",
            r"\b(?:publish|subscribe|consume|enqueue|ack|nack)\w*\s*\(",
            r"\bqueue\.(?:receive|pop|get|put|push|send)\w*\s*\(",
            r"\bOn\w+(?:Created|Updated|Deleted|Changed)\b", r"\b\w+(?:Created|Updated|Deleted|Changed)Event\b",
            r"\bmessage_?id\b|\bmsg\.(?:body|ack|nack|delete)\b",
        ),
    ),
    Axis(
        "load-and-shutdown",
        signals=(
            r"\bSIG(?:TERM|INT)\b|signal\.Notify|process\.on\(\s*['\"]SIG|\bgraceful",
            r"\.Shutdown\s*\(|ListenAndServe|\b(?:uvicorn|gunicorn|hypercorn|puma)\b|\bcreateServer\b",
            r"Promise\.(?:all|allSettled|race|any)\b|asyncio\.(?:gather|create_task|TaskGroup)\b",
            r"\bgo\s+func\b|\bgo\s+\w+(?:\.\w+)*\(|\berrgroup\b",
            r"\b(?:ThreadPoolExecutor|ProcessPoolExecutor|ExecutorService|CompletableFuture|WhenAll|Parallel\.For)",
            r"\bsemaphore|\bbackoff\b|\bretr(?:y|ies|ying)\b|circuit[-_ ]?breaker",
            r"connection[-_ ]?pool|\bpool_?size\b|\bmax_?connections\b|\bworker_?(?:pool|count|threads)\b",
            r"context\.With(?:Timeout|Deadline|Cancel)|\bCancellationToken\b|\bAbort(?:Controller|Signal)\b",
            r"\b\w*time_?out\w*",   # timeout, requestTimeout, READ_TIMEOUT_MS: a setting alone counts
        ),
    ),
    Axis(
        "money",
        signals=(
            r"\b(?:amounts?|prices?|pricing|currenc(?:y|ies)|money|monetary|payments?|payouts?|refund\w*"
            r"|invoice\w*|balance|tax|vat|discount\w*|subtotal|fees?|billing|ledger|wallet)\b",
            # Suffix forms start at a word boundary: an unanchored \w* rescans a long word
            # (base64, minified code) from every character, which is quadratic.
            # Decimal is case-sensitive: the type, not the word ("one decimal place").
            r"\b\w*cents\b", r"\bprice\w*", r"\b\w*charge\w*", r"(?-i:\b(?:Big)?Decimal\b)",
            r"\b(?:stripe|paypal|braintree|adyen)\b",
        ),
    ),
    Axis(
        "time",
        signals=(
            r"\b(?:datetime|timedelta|timezone|tzinfo|pytz|zoneinfo|dateutil)\b",
            r"\btime\.(?:time|monotonic|perf_counter|Now|Since|Until)\b|\bDate\.now\b|\bnew Date\b",
            r"\b(?:Instant|LocalDateTime|ZonedDateTime|OffsetDateTime|DateTimeOffset|ZoneId)\b",
            r"\bDateTime\.(?:Now|UtcNow|Today)\b|\bSystem\.(?:currentTimeMillis|nanoTime)\b",
            r"\b(?:ttl|expir\w*|lease\w*|cron\w*|schedul\w*|utc\w*|epoch|clock\w*|deadline)\b",
            r"\b\w*time_?out\w*",
            r"\b(?:moment|dayjs|date-fns|luxon|chrono)\b",
        ),
    ),
    Axis(
        "data-migrations",
        paths=("migration/", "migrations/", "migrate/", "alembic/versions/", "flyway/", "liquibase/",
               "schema.rb", "structure.sql", "*.sql", "*.prisma", "models.py", "models/"),
        languages=("sql",),
        signals=(
            r"\balter\s+table\b|\bcreate\s+(?:unique\s+)?index\b|\bdrop\s+(?:table|column|index)\b|\badd\s+column\b",
            r"\bbackfill|\bmigrat\w*", r"\b(?:add_column|remove_column|create_table|change_column|add_index)\b",
            r"\bop\.(?:add|drop|alter|create)_\w+",
            r"\bdb\.Column\b|\bmodels\.Model\b|@Entity\b|@Table\b|\bSchema::|\bknex\.schema\b",
        ),
    ),
    Axis(
        "dependencies",
        paths=("package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "requirements*.txt",
               "pyproject.toml", "setup.py", "setup.cfg", "pipfile", "pipfile.lock", "poetry.lock", "uv.lock",
               "go.mod", "go.sum", "cargo.toml", "cargo.lock", "pom.xml", "build.gradle", "build.gradle.kts",
               "*.csproj", "*.fsproj", "*.vbproj", "packages.config", "directory.packages.props", "gemfile",
               "gemfile.lock", "*.gemspec", "composer.json", "composer.lock", "package.swift", "package.resolved",
               "podfile", "podfile.lock", "vcpkg.json", "conanfile.txt", "conanfile.py",
               "module.bazel", "module.bazel.lock", "workspace.bazel", "flake.nix", "flake.lock",
               "vendor/", "third_party/", "third-party/", "thirdparty/", "external/",
               "license", "license.*", "notice", "notice.*", "copying", "copying.*"),
        signals=(
            r"SPDX-License-Identifier", r"\bGNU (?:Lesser |Affero )?General Public License\b",
            r"\bLicensed under the\b", r"\bMozilla Public License\b", r"\bPermission is hereby granted\b",
        ),
    ),
    Axis(
        "generated-output",
        paths=("generated/", "gen/", "__generated__/", "__snapshots__/", "golden/", "testdata/",
               "*.pb.go", "*_pb2.py", "*_pb2_grpc.py", "*.pb.ts", "*_pb.js", "*_pb.d.ts", "*.g.dart",
               "*.freezed.dart", "*.generated.*", "*.designer.cs", "*.g.cs", "*.snap", "*.golden",
               "*.proto", "*.graphql", "*.graphqls", "*.gql", "openapi*", "swagger*"),
        signals=(
            r"\bDO NOT EDIT\b", r"@generated\b", r"\bauto-?generated\b", r"\bgenerated by\b",
            r"go:generate", r"\bcodegen\b", r"\bprotoc\b", r"openapi-generator", r"\bsnapshots?\b|\bgolden\b",
        ),
    ),
    Axis(
        "public-interfaces",
        paths=("openapi*", "swagger*", "*.proto", "*.graphql", "*.graphqls", "*.gql", "*.d.ts", "*.pyi",
               "include/", "api/"),
        signals=(
            # Indentation is [ \t]*, not \s*: \s would run across blank lines from every line
            # start, which is quadratic in a long run of them.
            r"\b__all__\b", r"^[ \t]*pub\s+(?:fn|struct|enum|trait|mod|const|type|use)\b",
            r"^[ \t]*export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|interface|type|enum)\b",
            r"\bmodule\.exports\b|\bexports\.\w+\s*=",
            r"^[ \t]*public\s+(?:(?:sealed|abstract|static|final)\s+)*(?:class|interface|enum|record|struct)\b",
            # Go exports by capital letter: func Format(, func (r *T) Do(, type Report struct.
            r"(?-i:^func[ \t]+(?:\([^)\n]*\)[ \t]*)?[A-Z]\w*[ \t]*[\[(])",
            r"(?-i:^type[ \t]+[A-Z]\w*(?:\[|[ \t]+[\w*\[]))",
            r"\b(?:argparse|add_argument|add_parser|typer|commander|yargs|clap)\b|\bclick\.(?:option|argument|command|group)\b",
            r"\bcobra\.Command\b|\bflag\.(?:String|Int|Bool|Duration|Float64)\w*\(|#\[derive\([^)]*Parser",
            r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\b|\[Http(?:Get|Post|Put|Delete|Patch)\b",
            _ROUTE_DECORATOR, r"\brouter\.(?:get|post|put|delete|patch)\s*\(",
            r"@deprecated\b|\bDeprecationWarning\b|\bsemver\b",
        ),
    ),
    Axis(
        "privacy",
        signals=(
            r"\b(?:e-?mail\w*|phone\w*|ssn|passport\w*|date_?of_?birth|dob|birth_?date|birthday|post_?code"
            r"|zip_?code|ip_?address\w*|geoloc\w*|latitude|longitude|gdpr|ccpa|hipaa|pii|consent\w*|retention"
            r"|anonymi[sz]\w*|pseudonymi[sz]\w*|gender|ethnicity|medical|diagnos\w*)\b",
            r"\bsocial[-_ ]security\b|\bpersonal[-_ ]data\b|\bnational[-_ ]id\b",
            r"\b(?:first|last|full)_?name\b|\b(?:home|street|billing|shipping)_?address\b",
        ),
    ),
    Axis(
        "llm-calls",
        signals=(
            r"\b(?:anthropic|openai|langchain\w*|llama_?index|vertexai|bedrock\w*|ollama|mistralai|cohere|groq"
            r"|litellm|huggingface_hub)\b|\bgoogle\.genai\b|\bgoogle\.generativeai\b",
            r"@ai-sdk/|@anthropic-ai/",
            r"\bmessages\.create\b|\bchat\.completions\b|\bresponses\.create\b|\bgenerate_content\b|\binvoke_model\b",
            r"\bmax_tokens\b|\bmaxTokens\b|\bmax_output_tokens\b|\bsystem_?prompt\b|\bprompt_?template\b|\btool_?choice\b",
            r"\bclaude-[a-z0-9]|\bgpt-[0-9o]|\bgemini-[0-9]",
        ),
    ),
    Axis(
        "data-ml",
        paths=("*.ipynb", "notebooks/", "dags/", "dbt_project.yml", "pipelines/", "training/", "ml/"),
        signals=(
            r"\b(?:pandas|numpy|polars|pyspark|sklearn|scikit-learn|torch|tensorflow|keras|xgboost|lightgbm"
            r"|catboost|mlflow|airflow|dagster|prefect|great_expectations|onnx|dbt)\b",
            r"\bpd\.(?:read_\w+|DataFrame|merge|concat)\b|\bnp\.\w+",
            r"\b(?:predict(?:_proba)?|fit_transform|train_test_split|feature_store)\b|\.fit\s*\(",
            r"\bDataFrame\b|\bspark\.(?:read|sql|table)\b",
        ),
    ),
    Axis(
        "ui",
        paths=("*.tsx", "*.jsx", "*.vue", "*.svelte", "*.astro", "*.html", "*.htm", "*.css", "*.scss", "*.sass",
               "*.less", "*.erb", "*.cshtml", "*.razor", "*.xib", "*.storyboard", "*.xaml", "*.hbs", "*.jinja",
               "*.jinja2", "*.j2", "*.twig", "*.liquid", "*.po", "*.pot", "*.xliff", "*.xlf", "*.arb",
               "*.strings", "strings.xml", "templates/", "components/", "views/", "pages/", "res/layout/",
               "locales/", "locale/", "i18n/", "l10n/", "translations/"),
        signals=(
            r"\b(?:SwiftUI|UIKit|androidx\.compose|@Composable|react-dom|ReactDOM|useState|useEffect)\b",
            r"\baria-\w+|\btabindex\b|\brole=", r"\b(?:gettext|ngettext|i18n|l10n)\b|\bIntl\.",
        ),
    ),
    Axis(
        "mobile",
        paths=("androidmanifest.xml", "info.plist", "*.entitlements", "*.pbxproj", "*.xcconfig", "*.dart",
               "pubspec.yaml", "podfile", "ios/", "android/"),
        signals=(
            r"\b(?:UIApplication\w*|UIViewController|SwiftUI|WKWebView|AppCompatActivity|WorkManager"
            r"|BGTaskScheduler|react-native|flutter|capacitor|cordova)\b",
            r"\bandroid\.(?:app|content|os|permission)\b",
        ),
    ),
    Axis(
        "cross-platform",
        paths=("*.sh", "*.bash", "*.ps1", "*.psm1", "*.bat", "*.cmd", "makefile", ".gitattributes", ".editorconfig"),
        languages=("shell",),
        signals=(
            r"\bos\.path\b|\bos\.sep\b|\bpathlib\b|\bPath\(|\bpath\.(?:join|resolve|sep|normalize)\b",
            r"\bfilepath\.\w+|\bPath\.Combine\b|\bFile\.separator\b",
            r"\\r\\n|\bos\.linesep\b|\bline[-_ ]?endings?\b",
            r"\b(?:platform\.system|sys\.platform|process\.platform|runtime\.GOOS|target_os|RuntimeInformation|OSPlatform)\b",
            r"\bsubprocess\b|\bchild_process\b|\bexec\.Command\b|\bProcessBuilder\b|\bshell\s*=\s*True\b",
            r"\bencoding\s*=|\bgetpreferredencoding\b|\bsetlocale\b",
        ),
    ),
    Axis(
        "cloud-cost",
        # Provisioning only: CI workflows are infrastructure.md files too, but rarely cost money.
        paths=("*.tf", "*.tfvars", "*.tf.json", "*.tfvars.json", "*.hcl", "chart.yaml", "values.yaml",
               "kustomization.yaml", "k8s/", "kubernetes/", "helm/", "charts/", "kustomize/", "manifests/",
               "deploy/", "deployment/", "argocd/", "serverless.yml", "serverless.yaml", "cdk.json",
               "pulumi.yaml", "pulumi.*.yaml"),
        signals=(
            r"\b(?:boto3|botocore|aws_cdk|aws-cdk-lib|pulumi|cloudwatch|bigquery|snowflake|dynamodb|elasticache"
            r"|fargate|ec2|instance_type|autoscal\w*|provisioned\w*|egress|nat_gateway)\b",
            r"@aws-sdk/|\baws-sdk\b|\bgoogle\.cloud\b|@google-cloud/|@azure/|\bazure\.\w+",
            r"\bs3://|\bs3\.\w+|\bS3Client\b",
        ),
    ),
]

AXES: dict[str, Axis] = {}
for _axis in _AXES:
    _compiled = re.compile("|".join(f"(?:{s})" for s in _axis.signals), re.IGNORECASE | re.MULTILINE) \
        if _axis.signals else None
    AXES[_axis.name] = Axis(_axis.name, _axis.paths, _axis.languages, _axis.signals, _compiled)


def _path_matches(label: str, lower_path: str, name: str) -> bool:
    """Same rule shapes as detect_languages.PATH_RULES: "dir/" anywhere in the path, else a basename glob."""
    if label.endswith("/"):
        return f"/{label}" in f"/{lower_path}"
    return fnmatch.fnmatchcase(name, label)


def classify_axes(path: str, text: str | None = None, languages: tuple[str, ...] | list[str] = ()) -> list[str]:
    """Return the axes one file selects, in the order AXES lists them.

    `path` is repo-root-relative POSIX; `text` is the file's contents (None when they
    can't be read, such as a binary or a path with no revision to read from);
    `languages` are the language references detect_languages.py chose for the file.
    """
    posix = PurePosixPath(path)
    lower = str(posix).lower()
    name = posix.name.lower()
    out: list[str] = []
    for axis in AXES.values():
        if (any(lang in languages for lang in axis.languages)
                or any(_path_matches(label, lower, name) for label in axis.paths)
                or (text and axis.pattern is not None and axis.pattern.search(text))):
            out.append(axis.name)
    return out


def decode_text(data: bytes) -> str | None:
    """Bytes read from a file -> text to scan, or None for binary content.

    UTF-16 text is full of NUL bytes, so a byte-order mark is checked before the NUL test.
    """
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data[:MAX_SCAN_BYTES].decode("utf-16", "replace")
    if b"\0" in data[:8192]:
        return None
    return data[:MAX_SCAN_BYTES].decode("utf-8", "replace")
