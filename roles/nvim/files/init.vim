let mapleader = '-'

call plug#begin('~/.nvim/plugged')

" general plugins
" Use release branch (recommend)
Plug 'neoclide/coc.nvim', {'branch': 'release'}
Plug 'tpope/vim-surround'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-eunuch'

" fzf
Plug 'junegunn/fzf.vim'
" Plug '/usr/local/opt/fzf'

" git
Plug 'tpope/vim-fugitive'
Plug 'jreybert/vimagit'
Plug 'airblade/vim-gitgutter'

" nerdtree
Plug 'scrooloose/nerdtree'

" python
" Plug 'python-mode/python-mode', { 'for': 'python', 'branch': 'develop' }
" Plug 'davidhalter/jedi-vim'

" vim-airline
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'

call plug#end()

"fzf
set rtp+=$HOME/.fzf/
nnoremap <leader><C-f> :FZF<CR>

"nerdtree
nnoremap <leader><C-n> :NERDTreeToggle<CR>

"python-mode"
" let g:pymode_options_colorcolumn = 0
" let g:pymode_run_bind = '<leader>R'

let g:airline#extensions#ale#enabled = 1

" ultisnips
" let g:UltiSnipsExpandTrigger='<c-k>'
" let g:UltiSnipsJumpForwardTrigger='<c-b>'
" let g:UltiSnipsJumpBackwardTrigger='<c-z>'
" let g:UltiSnipsEditSplit='vertical'
" let g:UltiSnipsSnippetDirectories=[$HOME.'/.nvim/plugged/vim-snippets/UltiSnips', $HOME.'/.config/nvim/UltiSnips_custom']

" mappings
source $HOME/.config/nvim/mappings.vim

" misc settings
source $HOME/.config/nvim/misc.vim