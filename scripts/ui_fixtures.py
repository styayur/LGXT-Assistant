"""Synthetic bridge data, only imported by verification scripts."""
FIXTURE = r"""
window.__test = {calls:[], stopped:false, count:0, saved:[], settings:null};
const test = window.__test;
const defaults = {theme:'dark',language:'zh',startup:'new',reduceMotion:true,provider:'Local',endpoint:'http://localhost:11434/v1',model:'test-model',temperature:.7,contextMessages:40,maxTokens:4096,storeConversations:true,memoryEnabled:false,memory:'',debug:false,profiles:{}};
window.pywebview={api:{
 bootstrap:async()=>({settings:defaults,hasKey:false,conversations:[],prompts:[],username:'测试账号',savedUsername:'',export:{export_path:'test-output',export_word:true,export_pdf:false,export_word_include_answers:true,export_pdf_include_answers:true}}),
 save_conversation:async c=>{test.saved.push(c);return true;},
 save_workspace:async()=>true,
 save_settings:async s=>{test.settings=s;return {settings:s,hasKey:false};},
 start_chat:async m=>{test.calls.push({action:'chat',messages:m});test.count=0;test.stopped=false;return 'fixture-job';},
 poll_job:async(id,offset)=>{test.count++;let text='这是一段用于验证流式渲染的测试回复。'.repeat(Math.min(test.count,12));return {id,kind:'chat',done:test.stopped||test.count>=12,error:'',delta:text.slice(offset),offset:text.length,status:test.stopped?'已停止':'正在生成',progress:0,maximum:100};},
 stop_chat:async()=>{test.stopped=true;return true;},
 courses:async()=>Array.from({length:25},(_,i)=>({courseId:i+1,courseName:i===0?'大学物理 · 测试课程':`测试课程 ${i+1}`})),
 works:async id=>[{workId:101,workName:'动量与冲量 · 测试作业',chapterName:'第一章',grade:null,times:0,tryTimes:3,expireTime:'2026-12-31'}],
 question_document:async()=>null,
 save_question_document:async d=>d,
 questions:async id=>[{id:201,name:'动量守恒 · 测试题目',answer:'测试参考答案',imgurl:''}],
 submit_grade:async(id,grade)=>{test.calls.push({action:'submit',id,grade});return 'ok';},
 dashboard:async()=>({pending:2,completed:3,average:90,total:5,fetch_fail:0}),
 delete_conversation:async()=>true,
 export_chat:async()=>true,
}};
"""
