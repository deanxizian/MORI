import { test,expect } from '@playwright/test'
import { execFileSync,spawn } from 'node:child_process'
import { readFileSync,mkdtempSync,rmSync,writeFileSync,mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
let process:ReturnType<typeof spawn>,state:string
// Only disposable, named SIMULATED backend instances; no real device connection.
test.beforeAll(async()=>{state=mkdtempSync(tmpdir()+'/MORI-SIMULATED-e2e-');process=spawn(resolve('.venv/bin/python'),['-m','uvicorn','backend.mori.app:create_app','--factory','--host','127.0.0.1','--port','18765'],{env:{...globalThis.process.env,MORI_DATA_DIR:state},stdio:'ignore'});for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18765/health')).ok)return}catch{}await new Promise(r=>setTimeout(r,50))}throw Error('backend failed')})
test.afterAll(()=>{process?.kill();if(state)rmSync(state,{recursive:true,force:true})})
test('pair, explicit arm, bounded motion, stop, camera loss and persistent memory',async({page},testInfo)=>{
 const errors:string[]=[],consoleMessages:{level:string;text:string}[]=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type()))consoleMessages.push({level:m.type(),text:m.text()})})
 await page.goto('/');await page.getByLabel('服务地址').fill('http://127.0.0.1:18765');await page.getByLabel('一次性配对码').fill(readFileSync(state+'/pairing.txt','utf8'));await page.getByRole('button',{name:'配对并连接'}).click();await expect(page.getByText('● 在线',{exact:true})).toBeVisible()
 const claim=()=>page.getByRole('button',{name:'取得控制权 / 续租'}).click()
 await claim();await page.getByRole('checkbox',{name:'明确解锁此模拟设备'}).check();await page.getByRole('button',{name:'解锁模拟运动'}).click();await expect(page.getByText('模拟使能',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'前进 100 mm',exact:true}).click();await expect(page.locator('tbody tr').filter({hasText:'MOVE_DISTANCE'})).toContainText('COMPLETED',{timeout:6000})
 await page.getByRole('button',{name:'■ 停止移动'}).click();await expect(page.getByText('模拟使能',{exact:true})).toBeVisible()
 await claim();await page.getByRole('button',{name:'happy',exact:true}).click();await expect(page.getByRole('img',{name:'MORI 双眼：happy'})).toBeVisible()
 await expect(page.locator('.brand')).toContainText('V1.2')
 await expect(page.locator('vite-error-overlay')).toHaveCount(0)
 await page.screenshot({path:resolve(globalThis.process.env.MORI_REPORT_ROOT ?? 'reports/v1','design',testInfo.project.name+'-console.png'),fullPage:true})
 // Pointer release and window blur revoke renewal without DISARM.
 await claim();const forward=page.getByRole('button',{name:'向前',exact:true});await forward.scrollIntoViewIfNeeded();const box=await forward.boundingBox();if(!box)throw Error('missing dpad');await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();await page.waitForTimeout(150);await page.mouse.up();await expect(page.locator('.toolbar')).toContainText('未持有',{timeout:2000});await expect(page.getByText('模拟使能',{exact:true})).toBeVisible()
 await claim();await page.evaluate(()=>window.dispatchEvent(new Event('blur')));await expect(page.locator('.toolbar')).toContainText('未持有',{timeout:2000})

 // Switching panels releases previous movement lease; new mode needs explicit control.
 await page.getByRole('button',{name:'◉ 视觉与行为'}).click();await claim();await page.getByRole('button',{name:'TRACKING',exact:true}).click();await expect(page.getByRole('button',{name:/确认当前目标 track-1/})).toBeEnabled()
 await page.getByRole('button',{name:/确认当前目标 track-1/}).click();await page.getByRole('button',{name:'模拟底盘跟随'}).click();await expect(page.locator('tbody tr').filter({hasText:'FOLLOW'})).toContainText('RUNNING')
 await page.getByRole('button',{name:'多人 / 遮挡'}).click();await expect(page.locator('tbody tr').filter({hasText:'FOLLOW'})).toContainText('CANCELLED');await page.getByRole('button',{name:'OFF',exact:true}).click()
 await page.getByRole('button',{name:'▤ 长期记忆'}).click();await page.getByLabel('新增记忆').fill('SIMULATED 测试偏好：绿茶');await page.getByRole('checkbox',{name:'我确认保存这条内容'}).check();await page.getByRole('button',{name:'记住',exact:true}).click();await expect(page.locator('.memory-entry')).toHaveCount(1)
 const entry=page.locator('.memory-entry');await entry.locator('textarea').fill('SIMULATED 测试偏好：红茶');await entry.getByRole('button',{name:'确认纠正'}).click();await expect(entry.getByText('纠正历史 1')).toBeVisible();await entry.getByRole('button',{name:'删除',exact:true}).click();await expect(page.locator('.memory-entry')).toHaveCount(0)
 await page.getByRole('button',{name:'◌ 语音会话'}).click();await claim();await page.getByLabel('中文输入').fill('你好，测试对话');await page.getByRole('button',{name:'发送并播放'}).click();await expect(page.locator('.voice-response')).toContainText('模拟回复');await expect(page.locator('tbody tr').filter({hasText:'VOICE_SESSION'})).toContainText('COMPLETED',{timeout:8000});
 await page.getByRole('button',{name:'⚙ 设置与日志'}).click();await claim();await page.getByRole('button',{name:'模拟严重故障'}).click();await expect(page.locator('tbody tr').filter({hasText:'FAULT_STOP'})).toContainText('FAULT')
 const width=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,view:innerWidth}));expect(width.scroll).toBeLessThanOrEqual(width.view)
 await page.setViewportSize({width:844,height:390});await page.getByRole('button',{name:'⌘ 控制台'}).click();await expect(page.getByText('禁止',{exact:true})).toBeVisible()
 expect(errors).toEqual([])
 expect(consoleMessages).toEqual([])
 const evidence=resolve(globalThis.process.env.MORI_REPORT_ROOT ?? 'reports/v1','design');mkdirSync(evidence,{recursive:true});writeFileSync(resolve(evidence,testInfo.project.name+'-qa.json'),JSON.stringify({url:page.url(),title:await page.title(),pageErrors:errors,consoleMessages,source:'HOST_TEST',viewport:testInfo.project.use.viewport,rotatedViewport:page.viewportSize(),physical:'NOT_TESTED'},null,2))
})
