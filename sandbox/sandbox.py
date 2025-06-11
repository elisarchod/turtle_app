from dotenv import load_dotenv
from langgraph.pregel.io import AddableValuesDict
from langchain.globals import set_verbose

from turtleapp.src.workflows.graph import home_agent

load_dotenv(override=True)
set_verbose(True)


# import os
# os.environ["LANGCHAIN_PROJECT"]

# # msg = 'Generate 3 floats in [0.1, 3.3333], rounded to 4 decimals.'
# msg = 'i want 3 action movies, only names of movies known to locally'
# msg = 'another 3 action movies, only names of movies known to locally'
#
# msg = 'another 3 action movies names, only names of movies known to locally'
# msg = 'what 2 random movies i downloaded in torrent'
# ["recommend 3 comedy movies"],
# {"question": "recommend 3 comedy movies"},
# {"question": "recommend 2 bollywood movies"},
# {"question": "recommend a bollywood movie"},
# {"question": "recent movies i downloaded in torrent?"}

config = {"configurable": {"thread_id": "gen_int_13"}} # , "run_name": "gen_numbers_test_01"

result: AddableValuesDict = home_agent.invoke({"messages": "tell me the plot of terminator 2 ?"},
                                              config=config ) #
result['messages'][-1].pretty_print()



"""
1. **The Big Sick**
   - Plot: Kumail, a comedian in Chicago, navigates the complexities of dating Emily, a white woman, against his traditional Muslim parents' wishes. Their relationship faces a significant challenge when Emily is placed in a medically induced coma due to a serious infection. Kumail grows closer to Emily's parents as they endure her illness together, leading to a journey of self-discovery, cultural understanding, and love.
2. **The House**
   - Plot: Scott and Kate Johansen are desperate to fund their daughter's college tuition after losing her scholarship. They team up with their neighbor Frank to start an underground casino in his house. The casino operation runs smoothly until they catch the attention of the local authorities and a mob boss, leading to a series of comedic mishaps as they try to secure their daughter's future.
3. **Mr. Roosevelt**
   - Plot: Emily Martin returns to her hometown to come to terms with her past, staying with her ex-boyfriend and his new girlfriend. The film explores Emily's journey of self-discovery and the awkwardness of navigating relationships with humor and heart.

"""
result: AddableValuesDict = home_agent.invoke({"messages": "recommend 2 bollywood movies"}, )  # config=config,
result['messages'][-1].pretty_print()
"""
Here are two Bollywood movies that you might enjoy:
1. **Victoria & Abdul (2017)**: This film tells the extraordinary true story of an unexpected friendship in the later years of Queen Victoria's (Judi Dench) remarkable rule. When Abdul Karim (Ali Fazal), a young clerk, travels from India to participate in the Queen's Golden Jubilee, he is surprised to find favor with the Queen herself. As the Queen questions the constrictions of her long-held position, the two forge an unlikely and devoted alliance with a loyalty to one another that her household and inner circle all attempt to destroy. As the friendship deepens, the Queen begins to see a changing world through new eyes and joyfully reclaims her humanity.
2. **Growing Up Smith (2015)**: This is a coming-of-age story of a 10-year-old boy named Smith, from India, growing up in small-town America in 1979. As Smith's family tries to hold onto their Indian heritage while embracing the American Dream, Smith finds himself navigating the challenges of fitting in with his American peers and falling in love with the girl-next-door, Amy. The film beautifully captures the immigrant experience and the pursuit of identity between two contrasting cultures.
Both of these films offer unique perspectives on cultural integration, friendship, and the complexities of navigating different worlds.

"""
result: AddableValuesDict = home_agent.invoke({"messages": "recent movies i downloaded in torrent?"}, )  # config=config,
result['messages'][-1].pretty_print()
"""
The recent movies you've downloaded via torrent are:
1. **Click (2006) 1080p BrRip x264 - YIFY**
   - Path: `/downloads/Click (2006) [1080p]`
2. **Aquaman and the Lost Kingdom 2023 1080p WEB-DL DDP5.1 Atmos H.264-FLUX[TGx]**
   - Path: `/downloads/Aquaman.and.the.Lost.Kingdom.2023.1080p.WEB-DL.DDP5.1.Atmos.H.264-FLUX[TGx]`
These movies have been fully downloaded and are available in your specified download paths.
"""

