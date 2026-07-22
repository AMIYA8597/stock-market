#!/bin/bash
grep -rniE "mock|dummy|fake|placeholder|lorem|demoData|sample_data|_symbol_seed|Math\.random" \
  backend/app apps/web/src packages/*/src --include=*.py --include=*.ts --include=*.tsx \
  | grep -vE "backend/tests/|apps/web/e2e/|__fixtures__"
