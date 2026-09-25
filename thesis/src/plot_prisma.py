import matplotlib.pyplot as plt
import matplotlib.patches as patches

fig, ax = plt.subplots(figsize=(8, 10))
ax.axis('off')

# Nodes
boxes = {
    'id': {'pos': (0.5, 0.9), 'text': 'Identification\nScopus, IEEE, arXiv, SSRN, Scholar'},
    'screen': {'pos': (0.5, 0.7), 'text': 'Screening\nTitle & Abstract'},
    'eligibility': {'pos': (0.5, 0.5), 'text': 'Eligibility\nFull-text reading'},
    'included': {'pos': (0.5, 0.3), 'text': 'Included\n~40 papers'},
    'excluded1': {'pos': (0.8, 0.6), 'text': 'Excluded\nOff-topic, non-English,\nno OOS evaluation'},
    'excluded2': {'pos': (0.8, 0.4), 'text': 'Excluded\nPoor methodology,\nduplicates'}
}

for k, v in boxes.items():
    x, y = v['pos']
    ax.add_patch(patches.Rectangle((x - 0.2, y - 0.05), 0.4, 0.1, fill=True, color='lightblue', ec='black'))
    ax.text(x, y, v['text'], ha='center', va='center', fontsize=10)

# Arrows
ax.annotate('', xy=(0.5, 0.75), xytext=(0.5, 0.85), arrowprops=dict(arrowstyle="->"))
ax.annotate('', xy=(0.5, 0.55), xytext=(0.5, 0.65), arrowprops=dict(arrowstyle="->"))
ax.annotate('', xy=(0.5, 0.35), xytext=(0.5, 0.45), arrowprops=dict(arrowstyle="->"))
ax.annotate('', xy=(0.6, 0.6), xytext=(0.5, 0.65), arrowprops=dict(arrowstyle="->"))
ax.annotate('', xy=(0.6, 0.4), xytext=(0.5, 0.45), arrowprops=dict(arrowstyle="->"))

plt.title("PRISMA Flow Diagram")
plt.savefig('prisma_flow.png', bbox_inches='tight')
