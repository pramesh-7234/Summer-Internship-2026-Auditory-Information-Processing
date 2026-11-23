# Developmental auditory plasticity

This computational neuroscience project asks how an early auditory circuit can respond more strongly to a rare tone during training yet learn a larger response to the frequent tone. It follows the two tones through thalamic input, subplate and layer 4, then tests each on independent bursts after exposure.

[Read the scientific report](project/Research_Report.pdf) · [Explore the executed notebook](project/Auditory_Plasticity.ipynb) · [Browse the figures and source measurements](project/figures/README.md)

In eight paired early circuits, the rare tone evoked 1.503 Hz/cell more firing during training. After 100 tones, the formerly frequent tone had gained 0.058 Hz/cell more on isolated probes. Switching off subplate output depression largely removed the matched-target context effect. Adding timing-dependent plasticity to the subplate relay amplified the early frequent-tone advantage. These conclusions apply to immediate testing in the same developmental regime.

The simulator, scientific documentation and notebook live in `project/`. 

 [Installation, commands and data map](project/README.md)
