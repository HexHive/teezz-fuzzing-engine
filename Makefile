ENV_FILE=./docker/envs/taimen-km.env

PORT ?= 4242
TEE ?= optee
DEVICE_ID ?= 9WVDU18B06004395
CONFIG ?= optee_km.json
CONFIG_PATH ?= ./fuzz/config/${TEE}/${CONFIG}
MODE ?= dumb
IN ?= /tmp/optee-fuzz/in
OUT ?= /tmp/optee-fuzz/out
DURATION ?= 120
MISC ?= # e.g., -R and/or -M
NRUNS ?= 5
CRASH_SEQ_DIR ?= /path/to/crash/seq/dir


.PHONY: fuzz-tcp fuzz-adb fuzz-adb-eval test-fmt

help: ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

################################################################################
# Docker targets
################################################################################

build: Dockerfile compose.yaml ## Build the Docker container(s)
	docker compose build

run: ## Run the Docker container and spawn shell
	docker compose --env-file $(ENV_FILE) run --rm \
	  teezz-fuzzer "/bin/bash"

preprocess: ## Preprocessing
	docker compose --env-file $(ENV_FILE) run --rm \
	  teezz-preprocess /docker-preprocess.sh

prune-valdep: ## Get rid of false positive value dependencies
	docker compose --env-file $(ENV_FILE) run --rm \
	  teezz-preprocess /docker-prunevaldeps.sh

docker-fuzz: ## Get rid of false positive value dependencies
	docker compose --env-file $(ENV_FILE) run --name docker-fuzz --rm \
	  teezz-fuzzer /docker-fuzz.sh

docker-hisi-log: ## Get rid of false positive value dependencies
	docker exec -it docker-fuzz /bin/bash -c 'while [[ 1 ]]; do adb shell "su -c cat /dev/hisi_teelog"; sleep 3; done'

################################################################################
# TEEzz targets
################################################################################

fuzz-tcp:
	ipython --pdb -m fuzz.fuzz -- tcp \
	  ${MISC} \
	  -m ${MODE} \
	  -d ${DURATION} \
	  --in ${IN} --out ${OUT} \
	  --port ${PORT} ${TEE} ${CONFIG_PATH}

fuzz-adb:
	ipython --pdb -m fuzz.fuzz -- adb \
	  ${MISC} \
	  -m ${MODE} \
	  -d ${DURATION} \
	  --in ${IN} --out ${OUT} \
	  --port ${PORT} ${TEE} ${CONFIG_PATH} ${DEVICE_ID}

adb-dmesg: ## Get rid of false positive value dependencies
	bash -c 'while [[ 1 ]]; do adb shell "su -c dmesg --follow"; sleep 5; done'

adb-beanpod-log: ## Get rid of false positive value dependencies
	bash -c 'while [[ 1 ]]; do adb shell "su -c cat /dev/teei_config"; sleep 3; done'

triage-adb:
	ipython --pdb -m fuzz.triage -- adb \
	  --out ${OUT} \
	  --port ${PORT} ${TEE} ${CONFIG_PATH} ${CRASH_SEQ_DIR} ${DEVICE_ID}

probe-valdep-adb:
	ipython --pdb -m fuzz.probevaldep -- adb \
	  --in ${IN} --out ${OUT} \
	  --port ${PORT} ${TEE} ${CONFIG_PATH} ${DEVICE_ID}

fuzz-adb-eval:
	$(foreach i, \
	  $(shell seq 1 $(NRUNS)), \
	  echo "STARTING RUN ${i}"; \
	  adb -s ${DEVICE_ID} reboot; sleep 60; \
	  .venv/bin/ipython --pdb -m fuzz.fuzz -- adb \
	  	-m ${MODE} \
		-d ${DURATION} \
		--in ${IN} --out ${OUT} \
		--port ${PORT} ${TEE} ${CONFIG_PATH} ${DEVICE_ID}; \
	  mv ${OUT} $(shell dirname ${OUT})/$(basename ${CONFIG})-${DEVICE_ID}-${DURATION}-${i}; \
	  sleep 5; \
	 )

test-fmt:
	python -m unittest fuzz.fmt_recovery.test.test
