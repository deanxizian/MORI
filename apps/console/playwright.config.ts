import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'
export default defineConfig({testDir:'tests/e2e',workers:1,timeout:30000,reporter:[['list'],['json',{outputFile:resolve(process.env.MORI_REPORT_ROOT ?? 'reports/v1','browser-results.json')}]],use:{baseURL:'http://127.0.0.1:5173',trace:'retain-on-failure'},projects:[{name:'desktop',use:{viewport:{width:1440,height:1050}}},{name:'mobile-chromium',use:{viewport:{width:390,height:844},isMobile:true,hasTouch:true}}]})
