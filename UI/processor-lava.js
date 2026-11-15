(() => {
 const brand=document.querySelector('header .brand');
 function apply(){if(!brand)return;const image=brand.querySelector('img');if(image&&image.getAttribute('src')!=='/logo')image.src='/logo';const words=brand.querySelector('span');if(words&&words.textContent!=='LavaLabs'){words.replaceChildren();const strong=document.createElement('strong');strong.textContent='LavaLabs';words.append(strong);}}
 apply();if(brand)new MutationObserver(apply).observe(brand,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});
 document.title='LavaLabs · Flood processor';

 const panel=document.getElementById('processor-response');
 const status=document.getElementById('processor-response-status');
 const link=document.getElementById('processor-response-link');
 let pending;
 document.addEventListener('lavalabs:selection',()=>{
   pending?.abort();
   panel.hidden=true;
   link.hidden=true;
 });
 document.addEventListener('lavalabs:run',async ({detail:run})=>{
   pending?.abort();
   if(run.synthetic||document.getElementById('run').value!==run.run_id)return;
   pending=new AbortController();
   const signal=pending.signal;
   const id=encodeURIComponent(run.run_id);
   panel.hidden=false;
   status.textContent='Checking the saved run for priority locations…';
   try{
     const response=await fetch('/api/flood/runs/'+id+'/response?brief=true',{signal});
     if(!response.ok)throw new Error('Response evidence is unavailable for this analysis.');
     const brief=await response.json();
     if(signal.aborted)return;
     status.textContent=brief.lead
       ? 'Priority 1 begins with direct intersections and nearby communities, including '+brief.lead+'.'
       : 'Review the next checks for people, access and coverage gaps.';
     link.href='/processor/response?run='+id;
     link.hidden=false;
   }catch(error){
     if(!signal.aborted)status.textContent=error.message;
   }
 });
})();
