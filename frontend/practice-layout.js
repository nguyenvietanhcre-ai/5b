'use strict';
(() => {
  let stop=()=>{};
  function unmount(){stop();stop=()=>{};}
  function mount(root=document.querySelector('.practice-content-section')){
    unmount();if(!root)return;
    const stack=root.querySelector('.practice-sticky-stack');if(!stack)return;
    let frame=0;
    const measure=()=>{
      frame=0;if(!root.isConnected)return;
      const height=Math.min(innerHeight,window.visualViewport?.height||innerHeight);
      root.style.setProperty('--practice-visible-height',height+'px');
      const budget=Math.max(140,Math.min(height*.5,height-100));
      const natural=[...stack.children].reduce((sum,node)=>sum+node.scrollHeight+12,0);
      root.classList.toggle('practice-question-only',Boolean(stack.querySelector('.answers,.pilot-options,[data-answer-choice]'))&&natural>budget);
    };
    const queue=()=>{if(!frame)frame=requestAnimationFrame(measure);};
    const observer=new ResizeObserver(queue);observer.observe(root);observer.observe(stack);
    addEventListener('resize',queue);window.visualViewport?.addEventListener('resize',queue);measure();
    stop=()=>{observer.disconnect();cancelAnimationFrame(frame);removeEventListener('resize',queue);window.visualViewport?.removeEventListener('resize',queue);};
  }
  window.PracticeLayout={mount,unmount};
})();
