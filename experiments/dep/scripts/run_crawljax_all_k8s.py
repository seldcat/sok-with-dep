#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


APPS = {
    "addressbook": {
        "url": "http://web/addressbook-mod/addressbook/index.php",
        "web_image": "sotk-addressbook-web:local",
        "db": {
            "name": "mysql",
            "image": "sotk-addressbook-mysql:local",
            "port": 3306,
            "env": {"MYSQL_ROOT_PASSWORD": "root"},
            "command": ["--init-file", "/data/application/init.sql"],
        },
    },
    "drupal": {
        "url": "http://web/",
        "web_image": "sotk-drupal-web:local",
        "web_env": {
            "DRUPAL_USERNAME": "jAEkPot",
            "DRUPAL_PASSWORD": "jAEkPot",
            "DRUPAL_DATABASE_USER": "dbuser",
            "DRUPAL_DATABASE_PASSWORD": "dbpassword",
            "DRUPAL_DATABASE_NAME": "dbname",
        },
        "db": {
            "name": "mariadb",
            "image": "bitnamilegacy/mariadb:10.3",
            "port": 3306,
            "env": {
                "ALLOW_EMPTY_PASSWORD": "yes",
                "MARIADB_USER": "dbuser",
                "MARIADB_PASSWORD": "dbpassword",
                "MARIADB_DATABASE": "dbname",
            },
        },
    },
    "hotcrp": {
        "url": "http://web/index.php",
        "web_image": "sotk-hotcrp-web:local",
        "web_env": {
            "MYSQL_USER": "hotcrp",
            "MYSQL_PASSWORD": "hotcrp",
            "MYSQL_DATABASE": "hotcrp",
            "MYSQL_ROOT_PASSWORD": "root",
            "EXPERIMENT_ID": "dep-all",
        },
        "db": {
            "name": "mysql",
            "image": "mysql:8.0.28",
            "port": 3306,
            "env": {
                "MYSQL_ROOT_PASSWORD": "root",
                "MYSQL_DATABASE": "hotcrp",
                "MYSQL_USER": "hotcrp",
                "MYSQL_PASSWORD": "hotcrp",
            },
            "command": ["--default-authentication-plugin=mysql_native_password"],
            "sql": ROOT / "apps/hotcrp/dump.sql",
            "mount": "/docker-entrypoint-initdb.d/dump.sql",
        },
    },
    "joomla": {
        "url": "http://web/",
        "web_image": "sotk-joomla-web:local",
        "web_env": {
            "JOOMLA_DB_HOST": "mariadb",
            "JOOMLA_DB_USER": "dbuser",
            "JOOMLA_DB_PASSWORD": "dbpassword",
            "JOOMLA_DB_NAME": "dbname",
        },
        "db": {
            "name": "mariadb",
            "image": "bitnamilegacy/mariadb:10.3",
            "port": 3306,
            "env": {
                "ALLOW_EMPTY_PASSWORD": "yes",
                "MARIADB_USER": "dbuser",
                "MARIADB_PASSWORD": "dbpassword",
                "MARIADB_DATABASE": "dbname",
                "MARIADB_SQL_MODE": "NO_ZERO_IN_DATE,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION",
            },
        },
    },
    "owncloud": {
        "url": "http://web/",
        "web_image": "sotk-owncloud-web:local",
        "web_env": {
            "OWNCLOUD_DATABASE_HOST": "mariadb",
            "OWNCLOUD_DATABASE_PORT_NUMBER": "3306",
            "OWNCLOUD_DATABASE_USER": "bn_owncloud",
            "OWNCLOUD_DATABASE_NAME": "bitnami_owncloud",
            "OWNCLOUD_USERNAME": "jAEkPot",
            "OWNCLOUD_PASSWORD": "jAEkPot",
            "OWNCLOUD_EMAIL": "jaekpot@localhost.com",
            "APACHE_HTTP_PORT_NUMBER": "80",
            "ALLOW_EMPTY_PASSWORD": "yes",
            "OWNCLOUD_HOST": "web",
        },
        "db": {
            "name": "mariadb",
            "image": "bitnamilegacy/mariadb:10.3",
            "port": 3306,
            "env": {
                "ALLOW_EMPTY_PASSWORD": "yes",
                "MARIADB_USER": "bn_owncloud",
                "MARIADB_DATABASE": "bitnami_owncloud",
            },
        },
    },
    "phpbb2": {
        "url": "http://web/index.php",
        "web_image": "sotk-phpbb2-web:local",
        "db": {
            "name": "db",
            "image": "mysql:5.7.37",
            "port": 3306,
            "env": {
                "MYSQL_ROOT_PASSWORD": "root",
                "MYSQL_USER": "dbuser",
                "MYSQL_PASSWORD": "dbpass",
                "MYSQL_DATABASE": "dbname",
            },
            "sql": ROOT / "apps/phpbb2/dump.sql",
            "mount": "/docker-entrypoint-initdb.d/dump.sql",
        },
    },
    "prestashop": {
        "url": "http://web/",
        "web_image": "sotk-prestashop-web:local",
        "web_env": {
            "PS_INSTALL_AUTO": "1",
            "PS_DOMAIN": "web",
            "PS_LANGUAGE": "en",
            "ADMIN_MAIL": "jaekpot@localhost.com",
            "ADMIN_PASSWD": "jAEkPot123",
            "DB_SERVER": "mariadb",
            "DB_USER": "dbuser",
            "DB_PASSWD": "dbpassword",
            "DB_NAME": "dbname",
        },
        "db": {
            "name": "mariadb",
            "image": "bitnamilegacy/mariadb:10.3",
            "port": 3306,
            "env": {
                "ALLOW_EMPTY_PASSWORD": "yes",
                "MARIADB_USER": "dbuser",
                "MARIADB_PASSWORD": "dbpassword",
                "MARIADB_DATABASE": "dbname",
                "MARIADB_SQL_MODE": "NO_ZERO_IN_DATE,NO_ZERO_DATE,NO_ENGINE_SUBSTITUTION",
            },
        },
    },
    "scarf": {
        "url": "http://web/",
        "web_image": "sotk-scarf-web:local",
        "web_env": {
            "MYSQL_USER": "dbuser",
            "MYSQL_PASSWORD": "dbpass",
            "MYSQL_DATABASE": "dbname",
            "MYSQL_HOSTNAME": "db",
        },
        "db": {
            "name": "db",
            "image": "mysql:5.7.37",
            "port": 3306,
            "env": {
                "MYSQL_ROOT_PASSWORD": "root",
                "MYSQL_DATABASE": "dbname",
                "MYSQL_USER": "dbuser",
                "MYSQL_PASSWORD": "dbpass",
            },
            "command": ["--default-authentication-plugin=mysql_native_password"],
            "sql": ROOT / "apps/scarf/create_db.sql",
            "mount": "/docker-entrypoint-initdb.d/create_db.sql",
        },
    },
    "vanilla": {
        "url": "http://web/index.php",
        "web_image": "sotk-vanilla-web:local",
        "web_env": {
            "MYSQL_USER": "dbuser",
            "MYSQL_PASSWORD": "dbpass",
            "MYSQL_DATABASE": "dbname",
            "MYSQL_ROOT_PASSWORD": "root",
        },
        "db": {
            "name": "db",
            "image": "mysql:5.7.37",
            "port": 3306,
            "env": {
                "MYSQL_ROOT_PASSWORD": "root",
                "MYSQL_USER": "dbuser",
                "MYSQL_PASSWORD": "dbpass",
                "MYSQL_DATABASE": "dbname",
            },
            "command": ["--default-authentication-plugin=mysql_native_password"],
            "sql": ROOT / "apps/vanilla/dump.sql",
            "mount": "/docker-entrypoint-initdb.d/dump.sql",
        },
    },
    "wackopicko": {
        "url": "http://web/",
        "web_image": "sotk-wackopicko:local",
    },
    "wordpress": {
        "url": "http://web/",
        "web_image": "sotk-wordpress-web:local",
        "web_env": {
            "WORDPRESS_USERNAME": "jAEkPot",
            "WORDPRESS_PASSWORD": "jAEkPot",
            "WORDPRESS_DATABASE_USER": "dbuser",
            "WORDPRESS_DATABASE_PASSWORD": "dbpassword",
            "WORDPRESS_DATABASE_NAME": "dbname",
        },
        "db": {
            "name": "mariadb",
            "image": "bitnamilegacy/mariadb:10.3",
            "port": 3306,
            "env": {
                "ALLOW_EMPTY_PASSWORD": "yes",
                "MARIADB_USER": "dbuser",
                "MARIADB_PASSWORD": "dbpassword",
                "MARIADB_DATABASE": "dbname",
            },
        },
    },
}


def run(cmd, *, input_text=None, check=True, capture=False):
    print("+", " ".join(str(part) for part in cmd), flush=True)
    kwargs = {"text": True}
    if input_text is not None:
        kwargs["input"] = input_text
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.STDOUT
    result = subprocess.run(cmd, **kwargs)
    if check and result.returncode != 0:
        if capture and result.stdout:
            print(result.stdout, file=sys.stderr)
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.stdout if capture else ""


def env_list(env):
    return [{"name": key, "value": str(value)} for key, value in sorted((env or {}).items())]


def q(value):
    return json.dumps(str(value))


def yaml_list(items, indent):
    prefix = " " * indent
    lines = []
    for item in items:
        lines.append(f"{prefix}- {q(item)}")
    return "\n".join(lines)


def common_yaml(app, args):
    spec = APPS[app]
    ns = namespace(app)
    docs = [
        f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dep-results
  namespace: {ns}
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: {args.results_storage}
""",
        f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: dep-coverage
  namespace: {ns}
spec:
  accessModes: ["ReadWriteOnce"]
  resources:
    requests:
      storage: {args.coverage_storage}
""",
        f"""
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: {ns}
spec:
  selector:
    app: web
  ports:
    - name: http
      port: 80
      targetPort: 80
""",
        deployment_yaml(ns, "web", spec["web_image"], 80, spec.get("web_env")),
        crawler_job_yaml(ns, app, spec["url"], args),
    ]
    if "db" in spec:
        db = spec["db"]
        docs.extend(db_yaml(ns, db))
    return "\n---\n".join(docs)


def deployment_yaml(ns, name, image, port, env=None):
    env_block = ""
    if env:
        env_block = "\n          env:\n" + "\n".join(
            f"            - name: {key}\n              value: {q(value)}"
            for key, value in sorted(env.items())
        )
    coverage_mount = ""
    coverage_volume = ""
    if name == "web":
        coverage_mount = """
          volumeMounts:
            - name: coverage
              mountPath: /xdebug"""
        coverage_volume = """
      volumes:
        - name: coverage
          persistentVolumeClaim:
            claimName: dep-coverage"""
    return f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
        - name: {name}
          image: {image}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {port}{env_block}{coverage_mount}{coverage_volume}
"""


def db_yaml(ns, db):
    volume_mount = ""
    volume = ""
    if "sql" in db:
        key = db["sql"].name
        volume_mount = f"""
          volumeMounts:
            - name: db-init
              mountPath: {db["mount"]}
              subPath: {key}"""
        volume = """
      volumes:
        - name: db-init
          configMap:
            name: db-init"""
    command = ""
    if db.get("command"):
        command = "\n          args:\n" + yaml_list(db["command"], 12)
    env_block = "\n          env:\n" + "\n".join(
        f"            - name: {key}\n              value: {q(value)}" for key, value in sorted(db.get("env", {}).items())
    )
    return [
        f"""
apiVersion: v1
kind: Service
metadata:
  name: {db["name"]}
  namespace: {ns}
spec:
  selector:
    app: {db["name"]}
  ports:
    - name: mysql
      port: {db["port"]}
      targetPort: {db["port"]}
""",
        f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {db["name"]}
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {db["name"]}
  template:
    metadata:
      labels:
        app: {db["name"]}
    spec:
      containers:
        - name: {db["name"]}
          image: {db["image"]}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {db["port"]}{command}{env_block}{volume_mount}{volume}
""",
    ]


def crawler_job_yaml(ns, app, url, args):
    resource_arg = " --resources" if args.collect_resources else ""
    variants = []
    for variant in args.variants:
        if variant == "baseline":
            variants.append(("baseline", ""))
        elif variant == "dep":
            variants.append(("dep", "--compare-deps"))
        else:
            raise ValueError(f"unknown run variant: {variant}")
    variant_lines = "\n".join(
        f"              run_crawl {label} {extra}".rstrip()
        for label, extra in variants
    )
    return f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: crawljax-dep-comparison
  namespace: {ns}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      initContainers:
        - name: wait-for-web
          image: busybox:1.36
          command: ["sh", "-c", "until nc -z web 80; do sleep 2; done"]
      containers:
        - name: crawler
          image: {args.crawler_image}
          imagePullPolicy: IfNotPresent
          env:
            - name: CRAWL_TIMEOUT_MINUTES
              value: {q(args.timeout)}
          volumeMounts:
            - name: results
              mountPath: /results
            - name: coverage
              mountPath: /coverage
            - name: shm
              mountPath: /dev/shm
          command:
            - /bin/bash
            - -lc
            - |
              set -euo pipefail
              run_crawl() {{
                label="$1"
                shift
                rm -rf out
                mkdir -p out
                rm -rf /coverage/*
                ./docker-entrypoint.sh -t "${{CRAWL_TIMEOUT_MINUTES}}" \\
                  -a {args.algorithm} --nav {args.navigation} --app {app} \\
                  --no-save-screenshots --no-report-skeleton \\
                  --url {url}{resource_arg} "$@"
                rm -rf "/results/${{label}}"
                mkdir -p "/results/${{label}}"
                cp -a out/. "/results/${{label}}/"
                mkdir -p "/results/${{label}}/coverage"
                cp -a /coverage/. "/results/${{label}}/coverage/" || true
              }}
{variant_lines}
      volumes:
        - name: results
          persistentVolumeClaim:
            claimName: dep-results
        - name: coverage
          persistentVolumeClaim:
            claimName: dep-coverage
        - name: shm
          emptyDir:
            medium: Memory
            sizeLimit: 2Gi
"""


def namespace(app):
    return f"sotk-dep-{app}"


def create_configmaps(app):
    ns = namespace(app)
    db = APPS[app].get("db", {})
    if "sql" in db:
        run(["kubectl", "-n", ns, "create", "configmap", "db-init", f"--from-file={db['sql']}"])


def copy_results(app, output_dir):
    ns = namespace(app)
    target = output_dir / app
    if target.exists():
        shutil.rmtree(target)
    run([
        "kubectl",
        "-n",
        ns,
        "run",
        "dep-results-copy",
        "--image=busybox:1.36",
        "--restart=Never",
        "--overrides",
        '{"spec":{"containers":[{"name":"dep-results-copy","image":"busybox:1.36","command":["sh","-c","sleep 3600"],"volumeMounts":[{"name":"results","mountPath":"/results"}]}],"volumes":[{"name":"results","persistentVolumeClaim":{"claimName":"dep-results"}}]}}',
    ])
    run(["kubectl", "-n", ns, "wait", "--for=condition=Ready", "pod/dep-results-copy", "--timeout=60s"])
    run(["kubectl", "-n", ns, "cp", "dep-results-copy:/results", str(target)])
    run(["kubectl", "-n", ns, "delete", "pod", "dep-results-copy"], check=False)


def run_app(app, args):
    ns = namespace(app)
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    run(["kubectl", "delete", "namespace", ns, "--ignore-not-found=true"], check=False)
    run(["kubectl", "create", "namespace", ns])
    create_configmaps(app)
    run(
        ["kubectl", "apply", "-f", "-"],
        input_text=common_yaml(app, args),
    )
    try:
        run([
            "kubectl",
            "-n",
            ns,
            "wait",
            "--for=condition=complete",
            "job/crawljax-dep-comparison",
            f"--timeout={args.job_timeout}",
        ])
        copy_results(app, output_dir)
        status = "complete"
    except Exception:
        log_dir = output_dir / app
        log_dir.mkdir(parents=True, exist_ok=True)
        logs = run(["kubectl", "-n", ns, "logs", "job/crawljax-dep-comparison", "--all-containers=true"], check=False, capture=True)
        (log_dir / "job.log").write_text(logs or "", encoding="utf-8")
        status = "failed"
        raise
    finally:
        if args.cleanup:
            run(["kubectl", "delete", "namespace", ns, "--ignore-not-found=true"], check=False)
    return {"app": app, "status": status, "seconds": round(time.time() - started, 1)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps", nargs="+", default=sorted(APPS))
    parser.add_argument("--parallel", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=1, help="Crawljax timeout in minutes")
    parser.add_argument("--job-timeout", default="45m")
    parser.add_argument("--algorithm", default="url_full")
    parser.add_argument("--navigation", default="bfs")
    parser.add_argument("--variants", nargs="+", default=["baseline", "dep"], choices=["baseline", "dep"])
    parser.add_argument("--collect-resources", action="store_true")
    parser.add_argument("--results-storage", default="5Gi")
    parser.add_argument("--coverage-storage", default="5Gi")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "experiments/dep/results/all-calibration")
    parser.add_argument("--crawler-image", default="sotk-crawljax-dep:local")
    parser.add_argument("--no-cleanup", dest="cleanup", action="store_false")
    args = parser.parse_args()

    unknown = sorted(set(args.apps) - set(APPS))
    if unknown:
        raise SystemExit(f"unknown apps: {unknown}")

    results = []
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        futures = {executor.submit(run_app, app, args): app for app in args.apps}
        for future in as_completed(futures):
            app = futures[future]
            try:
                result = future.result()
                print(json.dumps(result), flush=True)
                results.append(result)
            except Exception as exc:
                print(json.dumps({"app": app, "status": "failed", "error": str(exc)}), file=sys.stderr, flush=True)
                results.append({"app": app, "status": "failed", "error": str(exc)})

    (args.output_dir / "run-status.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if any(row["status"] != "complete" for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
